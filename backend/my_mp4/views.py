import os
import yt_dlp
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .models import DownloadRequest
import json
import threading
import re

# Global dictionary to store progress
download_progress = {}

def progress_hook(d, download_request_id):
    """Enhanced progress hook with better percentage tracking"""
    if d['status'] == 'downloading':
        # Try multiple methods to get percentage
        percent = 0
        
        # Method 1: Use _percent_str
        if '_percent_str' in d:
            percent_str = d['_percent_str'].strip()
            if percent_str and percent_str != 'NA%':
                try:
                    percent = float(percent_str.replace('%', ''))
                except ValueError:
                    pass
        
        # Method 2: Calculate from bytes
        if percent == 0 and 'downloaded_bytes' in d and 'total_bytes' in d:
            try:
                if d['total_bytes'] > 0:
                    percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
            except (ZeroDivisionError, TypeError):
                pass
        
        # Method 3: Use total_bytes_estimate
        if percent == 0 and 'downloaded_bytes' in d and 'total_bytes_estimate' in d:
            try:
                if d['total_bytes_estimate'] > 0:
                    percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
            except (ZeroDivisionError, TypeError):
                pass
        
        if percent > 0:
            download_progress[download_request_id] = min(percent, 99)  # Cap at 99% until finished
            print(f"Download progress for {download_request_id}: {percent:.1f}%")
    
    elif d['status'] == 'finished':
        download_progress[download_request_id] = 100
        print(f"Download completed for {download_request_id}: 100%")

def extract_video_id(url):
    """Extract video ID from various YouTube URL formats"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'list=RD([0-9A-Za-z_-]{11})',  # YouTube Mix/Radio playlists
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def is_playlist_url(url):
    """Check if URL is a playlist"""
    return 'list=' in url and 'watch?v=' not in url

def download_video(url, format_type, download_request):
    try:
        media_dir = settings.MEDIA_ROOT
        os.makedirs(media_dir, exist_ok=True)
        
        download_progress[download_request.id] = 0
        print(f"Starting download for {download_request.id}")
        
        # Check if it's a playlist URL and convert to single video if needed
        if is_playlist_url(url):
            # Extract video ID if present
            video_id = extract_video_id(url)
            if video_id:
                url = f"https://www.youtube.com/watch?v={video_id}"
                print(f"Converted playlist URL to single video: {url}")
            else:
                raise Exception("Cannot download entire playlists. Please select a specific video.")
        
        # Base yt-dlp options
        ydl_opts = {
            'outtmpl': os.path.join(media_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [lambda d: progress_hook(d, download_request.id)],
            'noplaylist': True,  # CRITICAL: Only download single video, not playlist
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            },
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'no_warnings': False,
            'quiet': False,
        }
        
        if format_type == 'mp3':
            # Check if FFmpeg is available
            import shutil
            if shutil.which('ffmpeg') is None:
                ydl_opts.update({
                    'format': 'bestaudio[ext=m4a]/bestaudio/best',
                })
                print("WARNING: FFmpeg not found. Downloading audio in original format instead of MP3.")
            else:
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
        else:  # mp4
            ydl_opts.update({
                'format': 'best[ext=mp4]/best',
            })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Handle potential playlist extraction
            if 'entries' in info:
                # If it's a playlist, take only the first entry
                info = info['entries'][0]
            
            filename = ydl.prepare_filename(info)
            
            if format_type == 'mp3':
                # Update filename to .mp3 extension
                base_name = filename.rsplit('.', 1)[0]
                filename = base_name + '.mp3'
            
            # Ensure the file exists
            if not os.path.exists(filename):
                raise Exception(f"Downloaded file not found: {filename}")
            
            download_request.status = 'completed'
            download_request.file_path = filename
            download_request.video_title = info.get('title', 'Unknown Title')
            download_request.video_thumbnail = info.get('thumbnail', '')
            download_request.video_duration = info.get('duration', 0)
            download_request.save()
            
            # Ensure progress shows 100%
            download_progress[download_request.id] = 100
            print(f"✓ Download completed: {download_request.video_title}")
            
    except Exception as e:
        download_request.status = 'failed'
        download_request.error_message = str(e)
        download_request.save()
        if download_request.id in download_progress:
            del download_progress[download_request.id]
        print(f"✗ Error downloading {url}: {str(e)}")

@csrf_exempt
@require_http_methods(["POST"])
def start_download(request):
    try:
        data = json.loads(request.body)
        url = data.get('url')
        format_type = data.get('format', 'mp4')
        device_id = data.get('device_id')  # Get device_id from request
        
        if not url:
            return JsonResponse({'error': 'URL is required'}, status=400)
        
        if not device_id:
            return JsonResponse({'error': 'Device ID is required'}, status=400)
        
        # Validate URL
        if 'youtube.com' not in url and 'youtu.be' not in url:
            return JsonResponse({'error': 'Only YouTube URLs are supported'}, status=400)
        
        # Check if it's a playlist without a specific video
        if is_playlist_url(url) and not extract_video_id(url):
            return JsonResponse({'error': 'Please select a specific video from the playlist'}, status=400)
        
        download_request = DownloadRequest.objects.create(
            url=url,
            format_choice=format_type,
            status='processing',
            device_id=device_id,
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        thread = threading.Thread(
            target=download_video,
            args=(url, format_type, download_request)
        )
        thread.daemon = True
        thread.start()
        
        return JsonResponse({
            'message': 'Download started',
            'request_id': download_request.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def check_status(request, request_id):
    try:
        download_request = DownloadRequest.objects.get(id=request_id)
        progress = download_progress.get(request_id, 0)
        
        response_data = {
            'status': download_request.status,
            'file_path': download_request.file_path,
            'progress': round(progress, 1),
            'video_title': getattr(download_request, 'video_title', ''),
            'video_thumbnail': getattr(download_request, 'video_thumbnail', ''),
            'format': download_request.format_choice
        }
        
        if download_request.status == 'failed':
            response_data['error'] = getattr(download_request, 'error_message', 'Download failed')
        
        return JsonResponse(response_data)
        
    except DownloadRequest.DoesNotExist:
        return JsonResponse({'error': 'Download request not found'}, status=404)

@require_http_methods(["GET"])
def download_file(request):
    file_path = request.GET.get('path')
    
    if not file_path or not os.path.exists(file_path):
        return JsonResponse({'error': 'File not found'}, status=404)
    
    filename = os.path.basename(file_path)
    response = FileResponse(open(file_path, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@require_http_methods(["GET"])
def get_video_info(request):
    url = request.GET.get('url')
    
    if not url:
        return JsonResponse({'error': 'URL is required'}, status=400)
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,  # Only get info for single video
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Handle playlist case
            if 'entries' in info:
                info = info['entries'][0]
            
            return JsonResponse({
                'title': info.get('title', ''),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', ''),
                'thumbnail': info.get('thumbnail', ''),
                'formats': len(info.get('formats', [])),
            })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def get_download_history(request):
    try:
        device_id = request.GET.get('device_id')
        
        if not device_id:
            return JsonResponse({'error': 'Device ID is required'}, status=400)
        
        # Only return downloads for this specific device
        completed_downloads = DownloadRequest.objects.filter(
            status='completed', 
            device_id=device_id
        ).order_by('-created_at')
        
        downloads_list = []
        for download in completed_downloads:
            if download.file_path and os.path.exists(download.file_path):
                file_size = os.path.getsize(download.file_path)
                downloads_list.append({
                    'id': download.id,
                    'title': getattr(download, 'video_title', os.path.basename(download.file_path)),
                    'file_path': download.file_path,
                    'file_name': os.path.basename(download.file_path),
                    'file_size': file_size,
                    'format': download.format_choice,
                    'thumbnail': getattr(download, 'video_thumbnail', ''),
                    'duration': getattr(download, 'video_duration', 0),
                    'created_at': download.created_at.isoformat(),
                    'url': download.url
                })
        
        return JsonResponse(downloads_list, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_download(request, download_id):
    try:
        device_id = request.GET.get('device_id') or json.loads(request.body).get('device_id')
        
        if not device_id:
            return JsonResponse({'error': 'Device ID is required'}, status=400)
        
        # Only allow deletion if the download belongs to this device
        download = DownloadRequest.objects.get(id=download_id, device_id=device_id)
        
        if download.file_path and os.path.exists(download.file_path):
            os.remove(download.file_path)
            print(f"Deleted file: {download.file_path}")
        
        download.delete()
        
        return JsonResponse({'message': 'File deleted successfully'})
        
    except DownloadRequest.DoesNotExist:
        return JsonResponse({'error': 'Download not found or access denied'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def play_file(request):
    file_path = request.GET.get('path')
    
    if not file_path or not os.path.exists(file_path):
        return JsonResponse({'error': 'File not found'}, status=404)
    
    filename = os.path.basename(file_path)
    response = FileResponse(open(file_path, 'rb'))
    
    if file_path.lower().endswith('.mp4'):
        response['Content-Type'] = 'video/mp4'
    elif file_path.lower().endswith('.mp3'):
        response['Content-Type'] = 'audio/mpeg'
    
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response

@require_http_methods(["GET"])
def search_youtube(request):
    query = request.GET.get('q')
    
    if not query:
        return JsonResponse({'error': 'Search query is required'}, status=400)
    
    try:
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'default_search': 'ytsearch10',
            'noplaylist': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            
            results = []
            for entry in info.get('entries', []):
                results.append({
                    'id': entry.get('id'),
                    'title': entry.get('title'),
                    'uploader': entry.get('uploader'),
                    'duration': entry.get('duration'),
                    'thumbnail': entry.get('thumbnail'),
                    'url': f"https://www.youtube.com/watch?v={entry.get('id')}",
                    'view_count': entry.get('view_count'),
                })
            
            return JsonResponse(results, safe=False)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)