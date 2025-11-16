import os
import yt_dlp
import random
import time
import requests
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .models import DownloadRequest
import json
import threading
import re
import urllib3
import hashlib
import uuid

# Disable warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Global dictionaries
download_progress = {}

class YouTubeClientEmulator:
    def __init__(self):
        self.session = requests.Session()
        self.android_id = self.generate_android_id()
        self.device_id = self.generate_device_id()
        self.visitor_id = self.generate_visitor_data()
        
    def generate_android_id(self):
        """Generate realistic Android ID"""
        return f"android-{hashlib.md5(str(random.getrandbits(64)).encode()).hexdigest()[:16]}"
    
    def generate_device_id(self):
        """Generate realistic device ID"""
        return f"{random.getrandbits(32):08x}".upper()
    
    def generate_visitor_data(self):
        """Generate YouTube visitor data"""
        visitor_id = random.getrandbits(52)
        timestamp = int(time.time())
        return f"Cgt{visitor_id:x}YK{timestamp:x}="
    
    def get_mobile_headers(self):
        """Headers that mimic official YouTube Android app"""
        return {
            'User-Agent': 'com.google.android.youtube/17.36.4 (Linux; U; Android 11; en_US) gzip',
            'X-YouTube-Client-Name': '3',
            'X-YouTube-Client-Version': '17.36.4',
            'X-YouTube-Device': 'android',
            'X-YouTube-CLIENT-PROTO-VERSION': '1',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
    
    def get_web_headers(self):
        """Headers that mimic official YouTube web client"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'DNT': '1',
        }
    
    def get_tv_headers(self):
        """Headers that mimic YouTube on Smart TV"""
        return {
            'User-Agent': 'Mozilla/5.0 (SMART-TV; Linux; Tizen 5.5) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/3.0 Chrome/85.0.4183.93 TV Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }

    def create_authentic_ydl_opts(self, download_request_id, format_type, client_type="mobile"):
        """Create yt-dlp options that perfectly mimic official YouTube clients"""
        
        media_dir = settings.MEDIA_ROOT
        
        # Base options for authentic behavior
        ydl_opts = {
            'outtmpl': os.path.join(media_dir, '%(title).100s.%(ext)s'),
            'progress_hooks': [lambda d: progress_hook(d, download_request_id)],
            'noplaylist': True,
            
            # Gentle settings that don't trigger alarms
            'retries': 3,
            'fragment_retries': 3,
            'file_access_retries': 2,
            'skip_unavailable_fragments': False,
            'continuedl': True,
            'ignoreerrors': False,
            'no_overwrites': True,
            
            # Network settings that look human
            'socket_timeout': 30,
            'source_address': None,
            
            # Certificate settings
            'no_check_certificate': False,
            'prefer_insecure': False,
            'verbose': False,
            'no_warnings': True,
            'quiet': True,
            
            # Rate limiting that looks natural
            'throttled_rate': None,
            'ratelimit': None,
            'buffer_size': 65536,
            'http_chunk_size': 10485760,
            
            # Download optimization
            'concurrent_fragment_downloads': 1,  # Single connection like real clients
            'limit_rate': None,
        }
        
        # Client-specific configurations
        if client_type == "mobile":
            ydl_opts.update({
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android'],
                        'player_skip': [],
                    }
                },
                'http_headers': self.get_mobile_headers(),
            })
        elif client_type == "web":
            ydl_opts.update({
                'extractor_args': {
                    'youtube': {
                        'player_client': ['web'],
                        'player_skip': [],
                    }
                },
                'http_headers': self.get_web_headers(),
            })
        elif client_type == "tv":
            ydl_opts.update({
                'extractor_args': {
                    'youtube': {
                        'player_client': ['tv_html5'],
                        'player_skip': [],
                    }
                },
                'http_headers': self.get_tv_headers(),
            })
        
        # Format-specific options
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
                'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',
            })
        
        return ydl_opts

    def download_as_client(self, url, format_type, download_request, max_attempts=3):
        """Download video by perfectly mimicking official YouTube clients"""
        
        client_types = ["mobile", "web", "tv"]
        random.shuffle(client_types)  # Randomize client order
        
        for attempt, client_type in enumerate(client_types):
            try:
                print(f"🎭 Attempt {attempt + 1}: Mimicking YouTube {client_type.upper()} client")
                
                media_dir = settings.MEDIA_ROOT
                os.makedirs(media_dir, exist_ok=True)
                
                download_progress[download_request.id] = 0
                
                # Natural delay between attempts
                if attempt > 0:
                    delay = random.uniform(2, 8)  # Natural human delay
                    print(f"⏳ Natural delay: {delay:.1f}s")
                    time.sleep(delay)
                
                # Convert playlist URLs if needed
                if self.is_playlist_url(url):
                    video_id = self.extract_video_id(url)
                    if video_id:
                        url = f"https://www.youtube.com/watch?v={video_id}"
                        print(f"🔀 Converted to single video: {url}")
                
                # Get authentic client options
                ydl_opts = self.create_authentic_ydl_opts(download_request.id, format_type, client_type)
                
                print(f"   Client: {client_type.upper()}")
                print(f"   User-Agent: {ydl_opts['http_headers']['User-Agent'][:40]}...")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    
                    if 'entries' in info:
                        info = info['entries'][0]
                    
                    filename = ydl.prepare_filename(info)
                    
                    if format_type == 'mp3':
                        base_name = filename.rsplit('.', 1)[0]
                        filename = base_name + '.mp3'
                    
                    # Verify file exists
                    if not os.path.exists(filename):
                        raise Exception(f"Downloaded file not found: {filename}")
                    
                    if os.path.getsize(filename) == 0:
                        raise Exception(f"Empty file: {filename}")
                    
                    # Success - update database
                    download_request.status = 'completed'
                    download_request.file_path = filename
                    download_request.video_title = info.get('title', 'Unknown Title')
                    download_request.video_thumbnail = info.get('thumbnail', '')
                    download_request.video_duration = info.get('duration', 0)
                    download_request.save()
                    
                    download_progress[download_request.id] = 100
                    print(f"✅ SUCCESS as {client_type.upper()} client: {download_request.video_title}")
                    return True
                    
            except Exception as e:
                error_msg = str(e)
                print(f"❌ {client_type.upper()} client failed: {error_msg}")
                
                # Don't retry immediately - wait a bit
                time.sleep(random.uniform(1, 3))
                
                if attempt == len(client_types) - 1:
                    download_request.status = 'failed'
                    download_request.error_message = f"All client emulations failed: {error_msg}"
                    download_request.save()
                    if download_request.id in download_progress:
                        del download_progress[download_request.id]
                    print(f"💔 All YouTube client emulations failed")
                    return False
        
        return False

    def extract_video_id(self, url):
        """Extract video ID from URL"""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})',
            r'youtu\.be\/([0-9A-Za-z_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def is_playlist_url(self, url):
        """Check if URL is a playlist"""
        return 'list=' in url and 'watch?v=' not in url

# Initialize YouTube client emulator
youtube_client = YouTubeClientEmulator()

def progress_hook(d, download_request_id):
    """Progress hook with natural pacing"""
    if d['status'] == 'downloading':
        percent = 0
        
        if '_percent_str' in d:
            percent_str = d['_percent_str'].strip()
            if percent_str and percent_str != 'NA%':
                try:
                    percent = float(percent_str.replace('%', ''))
                except ValueError:
                    pass
        
        if percent == 0 and 'downloaded_bytes' in d and 'total_bytes' in d:
            try:
                if d['total_bytes'] > 0:
                    percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
            except (ZeroDivisionError, TypeError):
                pass
        
        if percent == 0 and 'downloaded_bytes' in d and 'total_bytes_estimate' in d:
            try:
                if d['total_bytes_estimate'] > 0:
                    percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
            except (ZeroDivisionError, TypeError):
                pass
        
        if percent > 0:
            download_progress[download_request_id] = min(percent, 99)
            # Natural progress updates
            if percent % 10 == 0:  # Only log every 10% to avoid spam
                print(f"📥 Progress: {percent:.1f}%")
    
    elif d['status'] == 'finished':
        download_progress[download_request_id] = 100
        print(f"✅ Download complete!")

def download_video(url, format_type, download_request):
    """Main download function using YouTube client emulation"""
    print(f"🎭 Starting YouTube client emulation for: {url}")
    
    success = youtube_client.download_as_client(url, format_type, download_request)
    
    if not success:
        print("💡 Tip: Try again later - YouTube might be rate limiting")
        download_request.status = 'failed'
        download_request.error_message = 'YouTube client emulation failed - try again in a few minutes'
        download_request.save()

@csrf_exempt
@require_http_methods(["POST"])
def start_download(request):
    try:
        data = json.loads(request.body)
        url = data.get('url')
        format_type = data.get('format', 'mp4')
        device_id = data.get('device_id')
        
        if not url:
            return JsonResponse({'error': 'URL is required'}, status=400)
        
        if not device_id:
            return JsonResponse({'error': 'Device ID is required'}, status=400)
        
        # Enhanced URL validation
        if 'youtube.com' not in url and 'youtu.be' not in url:
            return JsonResponse({'error': 'Only YouTube URLs are supported'}, status=400)
        
        # Check for playlist
        if youtube_client.is_playlist_url(url) and not youtube_client.extract_video_id(url):
            return JsonResponse({'error': 'Please select a specific video from the playlist'}, status=400)
        
        download_request = DownloadRequest.objects.create(
            url=url,
            format_choice=format_type,
            status='processing',
            device_id=device_id,
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Start download with client emulation
        thread = threading.Thread(
            target=download_video,
            args=(url, format_type, download_request)
        )
        thread.daemon = True
        thread.start()
        
        return JsonResponse({
            'message': 'Download started using YouTube client emulation',
            'request_id': download_request.id,
            'method': 'YouTube Client Emulation'
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Download startup failed: {str(e)}'}, status=500)

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
            'format': download_request.format_choice,
            'method': 'YouTube Client'
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
        # Use mobile client for info extraction
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                }
            },
            'http_headers': youtube_client.get_mobile_headers(),
            'no_check_certificate': False,
            'ignoreerrors': False,
            'extractor_retries': 2,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info:
                info = info['entries'][0]
            
            return JsonResponse({
                'title': info.get('title', ''),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', ''),
                'thumbnail': info.get('thumbnail', ''),
                'formats': len(info.get('formats', [])),
                'view_count': info.get('view_count', 0),
            })
            
    except Exception as e:
        return JsonResponse({'error': f'Info extraction failed: {str(e)}'}, status=500)

@require_http_methods(["GET"])
def get_download_history(request):
    try:
        device_id = request.GET.get('device_id')
        
        if not device_id:
            return JsonResponse({'error': 'Device ID is required'}, status=400)
        
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
        
        download = DownloadRequest.objects.get(id=download_id, device_id=device_id)
        
        if download.file_path and os.path.exists(download.file_path):
            os.remove(download.file_path)
            print(f"🗑️ Deleted file: {download.file_path}")
        
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
        # Use web client for search
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'default_search': 'ytsearch10',
            'noplaylist': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['web'],
                }
            },
            'http_headers': youtube_client.get_web_headers(),
            'no_check_certificate': False,
            'ignoreerrors': True,
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
        return JsonResponse({'error': f'Search failed: {str(e)}'}, status=500)

@require_http_methods(["GET"])
def client_status(request):
    """Get YouTube client emulator status"""
    status = {
        'method': 'YouTube Client Emulation',
        'clients': ['Mobile App', 'Web Browser', 'Smart TV'],
        'strategy': 'Mimic official YouTube clients',
        'aggression': 'Low (Stealth)',
        'success_rate': 'High',
    }
    return JsonResponse(status)

# System cleanup
def cleanup_old_downloads():
    """Clean up old download files"""
    try:
        media_dir = settings.MEDIA_ROOT
        if os.path.exists(media_dir):
            for filename in os.listdir(media_dir):
                file_path = os.path.join(media_dir, filename)
                # Delete files older than 24 hours
                if os.path.isfile(file_path):
                    file_age = time.time() - os.path.getctime(file_path)
                    if file_age > 86400:  # 24 hours
                        os.remove(file_path)
                        print(f"🧹 Cleaned up: {filename}")
    except Exception as e:
        print(f"Cleanup failed: {e}")

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_downloads)
cleanup_thread.daemon = True
cleanup_thread.start()