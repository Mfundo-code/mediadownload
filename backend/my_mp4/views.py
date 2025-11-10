import os
import yt_dlp
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .models import DownloadRequest
import json
import threading
import glob

# Global dictionary to store progress
download_progress = {}

def progress_hook(d, download_request_id):
    if d['status'] == 'downloading':
        if '_percent_str' in d:
            percent_str = d['_percent_str'].strip()
            if percent_str and percent_str != 'NA%':
                # Extract numeric percentage
                try:
                    percent = float(percent_str.replace('%', ''))
                    download_progress[download_request_id] = percent
                    print(f"Download progress for {download_request_id}: {percent}%")
                except ValueError:
                    pass
        elif 'downloaded_bytes' in d and 'total_bytes' in d:
            # Calculate percentage from bytes if percentage string is not available
            try:
                percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                download_progress[download_request_id] = percent
                print(f"Download progress for {download_request_id}: {percent:.1f}%")
            except (ZeroDivisionError, TypeError):
                pass
    elif d['status'] == 'finished':
        download_progress[download_request_id] = 100
        print(f"Download completed for {download_request_id}: 100%")

def download_video(url, format_type, download_request):
    try:
        # Create media directory if it doesn't exist
        media_dir = settings.MEDIA_ROOT
        os.makedirs(media_dir, exist_ok=True)
        
        # Initialize progress
        download_progress[download_request.id] = 0
        print(f"Starting download for {download_request.id}")
        
        ydl_opts = {
            'outtmpl': os.path.join(media_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [lambda d: progress_hook(d, download_request.id)],
        }
        
        if format_type == 'mp3':
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
            filename = ydl.prepare_filename(info)
            
            if format_type == 'mp3':
                filename = filename.rsplit('.', 1)[0] + '.mp3'
            
            # Store additional info
            download_request.status = 'completed'
            download_request.file_path = filename
            download_request.video_title = info.get('title', 'Unknown Title')
            download_request.video_thumbnail = info.get('thumbnail', '')
            download_request.video_duration = info.get('duration', 0)
            download_request.save()
            
            # Clean up progress tracking
            if download_request.id in download_progress:
                del download_progress[download_request.id]
            
    except Exception as e:
        download_request.status = 'failed'
        download_request.save()
        # Clean up progress tracking on error
        if download_request.id in download_progress:
            del download_progress[download_request.id]
        print(f"Error downloading {url}: {str(e)}")

@csrf_exempt
@require_http_methods(["POST"])
def start_download(request):
    try:
        data = json.loads(request.body)
        url = data.get('url')
        format_type = data.get('format', 'mp4')
        
        if not url:
            return JsonResponse({'error': 'URL is required'}, status=400)
        
        # Create download request record
        download_request = DownloadRequest.objects.create(
            url=url,
            format_choice=format_type,
            status='processing'
        )
        
        # Start download in background thread
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
        
        # Get current progress
        progress = download_progress.get(request_id, 0)
        
        print(f"Status check for {request_id}: {progress}%")
        
        return JsonResponse({
            'status': download_request.status,
            'file_path': download_request.file_path,
            'progress': progress,
            'video_title': getattr(download_request, 'video_title', ''),
            'video_thumbnail': getattr(download_request, 'video_thumbnail', '')
        })
        
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
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
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
    """Get all completed downloads"""
    try:
        completed_downloads = DownloadRequest.objects.filter(status='completed').order_by('-created_at')
        
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
    """Delete a downloaded file"""
    try:
        download = DownloadRequest.objects.get(id=download_id)
        
        if download.file_path and os.path.exists(download.file_path):
            os.remove(download.file_path)
            print(f"Deleted file: {download.file_path}")
        
        download.delete()
        
        return JsonResponse({'message': 'File deleted successfully'})
        
    except DownloadRequest.DoesNotExist:
        return JsonResponse({'error': 'Download not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def play_file(request):
    """Stream file for playing in browser"""
    file_path = request.GET.get('path')
    
    if not file_path or not os.path.exists(file_path):
        return JsonResponse({'error': 'File not found'}, status=404)
    
    filename = os.path.basename(file_path)
    response = FileResponse(open(file_path, 'rb'))
    
    # Set content type based on file extension
    if file_path.lower().endswith('.mp4'):
        response['Content-Type'] = 'video/mp4'
    elif file_path.lower().endswith('.mp3'):
        response['Content-Type'] = 'audio/mpeg'
    
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response