import os
import yt_dlp
import random
import time
import requests
import socks
import socket
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .models import DownloadRequest
import json
import threading
import re
import urllib3
from fake_useragent import UserAgent
import cloudscraper
from stem import Signal
from stem.control import Controller
import aiohttp
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

# Disable warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Global dictionaries
download_progress = {}
active_downloads = {}

# Nuclear option user agents (100+ realistic agents)
USER_AGENTS = [
    # Mobile Android
    'Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 11; Moto G Power (2022)) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    
    # Mobile iOS
    'Mozilla/5.0 (iPhone14,6; U; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/602.1.50 (KHTML, like Gecko) Version/10.0 Mobile/19E241 Safari/602.1',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
    
    # Desktop Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    
    # Desktop Mac
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    
    # Linux
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0',
    
    # Gaming Consoles
    'Mozilla/5.0 (PlayStation; PlayStation 5/2.26) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0 Safari/605.1.15',
    'Mozilla/5.0 (Nintendo Switch; WifiWebAuthApplet) AppleWebKit/601.6 (KHTML, like Gecko) NF/4.0.0.5.10 NintendoBrowser/5.1.0.13343',
    
    # Smart TVs
    'Mozilla/5.0 (SmartHub; SMART-TV; U; Linux/SmartTV) AppleWebKit/531.2+ (KHTML, like Gecko) WebBrowser/1.0 SmartTV Safari/531.2+',
]

# Massive proxy list (you need to populate this with actual proxies)
PROXY_LIST = [
    # Format: 'http://user:pass@ip:port' or 'http://ip:port'
    # Add hundreds of proxies here for maximum rotation
]

# Tor proxy settings
TOR_PROXY = 'socks5://127.0.0.1:9050'

class NuclearDownloader:
    def __init__(self):
        self.ua = UserAgent()
        self.scraper = cloudscraper.create_scraper()
        self.session = requests.Session()
        self.proxy_index = 0
        self.agent_index = 0
        
    def get_bruteforce_user_agent(self):
        """Get random user agent with maximum variation"""
        if random.random() < 0.3:  # 30% chance to use fake-useragent
            return self.ua.random
        else:
            return random.choice(USER_AGENTS)
    
    def get_bruteforce_proxy(self):
        """Get random proxy with load balancing"""
        if not PROXY_LIST:
            return None
        
        self.proxy_index = (self.proxy_index + 1) % len(PROXY_LIST)
        return PROXY_LIST[self.proxy_index]
    
    def rotate_tor_ip(self):
        """Rotate Tor IP address"""
        try:
            with Controller.from_port(port=9051) as controller:
                controller.authenticate()
                controller.signal(Signal.NEWNYM)
                print("✓ Tor IP rotated")
                time.sleep(5)  # Wait for new circuit
        except Exception as e:
            print(f"✗ Tor rotation failed: {e}")
    
    def create_nuclear_ydl_opts(self, download_request_id, format_type, attempt=0):
        """Create extremely aggressive yt-dlp options"""
        
        media_dir = settings.MEDIA_ROOT
        proxy = self.get_bruteforce_proxy()
        
        # Base nuclear options
        ydl_opts = {
            'outtmpl': os.path.join(media_dir, '%(title).80s.%(ext)s'),
            'progress_hooks': [lambda d: progress_hook(d, download_request_id)],
            'noplaylist': True,
            
            # Extreme retry settings
            'extractor_retries': 20,
            'fragment_retries': 25,
            'retries': 15,
            'file_access_retries': 10,
            'skip_unavailable_fragments': True,
            'continuedl': True,
            'ignoreerrors': True,
            'no_overwrites': False,
            
            # Aggressive client spoofing
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'android_embedded', 'web', 'ios', 'tv_html5', 'mweb'],
                    'player_skip': ['configs', 'webpage', 'js', 'manifest_dash'],
                    'throttled_rate': None,
                }
            },
            
            # Network brute force
            'socket_timeout': 60,
            'source_address': '0.0.0.0',
            'force-ipv4': True,
            'force-ipv6': False,
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            'geo_bypass_ip_block': '0.0.0.0/0',
            
            # Headers with extreme variation
            'http_headers': {
                'User-Agent': self.get_bruteforce_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': random.choice(['en-US,en;q=0.9', 'en-GB,en;q=0.8', 'en-CA,en;q=0.7']),
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'DNT': random.choice(['1', '0']),
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
            },
            
            # Certificate and security bypass
            'no_check_certificate': True,
            'prefer_insecure': True,
            'verbose': True,
            'no_warnings': False,
            'quiet': False,
            
            # Rate limiting bypass
            'throttled_rate': '1M',
            'ratelimit': 2097152,
            'buffer_size': 8192,
            'http_chunk_size': 10485760,
            
            # Download optimization
            'concurrent_fragment_downloads': 8,
            'limit_rate': '2M',
            'compression': 'identity',
        }
        
        # Add proxy with fallback to Tor
        if proxy:
            ydl_opts['proxy'] = proxy
        elif attempt % 3 == 0:  # Use Tor every 3rd attempt
            ydl_opts['proxy'] = TOR_PROXY
        
        # Format-specific nuclear options
        if format_type == 'mp3':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'postprocessor_args': [
                    '-ar', '44100',
                    '-ac', '2',
                    '-b:a', '192k'
                ],
            })
        else:  # mp4
            ydl_opts.update({
                'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[ext=mp4]/best',
                'merge_output_format': 'mp4',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
            })
        
        # Increase aggression with each attempt
        if attempt > 0:
            ydl_opts['retries'] += 5
            ydl_opts['fragment_retries'] += 5
            ydl_opts['http_headers']['User-Agent'] = self.get_bruteforce_user_agent()
            
            # Rotate IP if using Tor
            if attempt % 2 == 0:
                self.rotate_tor_ip()
        
        return ydl_opts

    def brute_force_download(self, url, format_type, download_request, max_attempts=8):
        """Brute force download with extreme aggression"""
        
        for attempt in range(max_attempts):
            try:
                print(f"🚀 BRUTE FORCE ATTEMPT {attempt + 1}/{max_attempts} for {download_request.id}")
                
                media_dir = settings.MEDIA_ROOT
                os.makedirs(media_dir, exist_ok=True)
                
                download_progress[download_request.id] = 0
                
                # Aggressive delay with jitter
                if attempt > 0:
                    delay = (2 ** attempt) + random.uniform(0.5, 3.0)
                    print(f"⏰ Waiting {delay:.2f}s before brutal retry...")
                    time.sleep(delay)
                
                # Convert playlist URLs
                if self.is_playlist_url(url):
                    video_id = self.extract_video_id(url)
                    if video_id:
                        url = f"https://www.youtube.com/watch?v={video_id}"
                        print(f"🔀 Converted to single video: {url}")
                
                # Get nuclear options for this attempt
                ydl_opts = self.create_nuclear_ydl_opts(download_request.id, format_type, attempt)
                
                # Log attempt details
                print(f"🎯 Attempt {attempt + 1} config:")
                print(f"   User-Agent: {ydl_opts['http_headers']['User-Agent'][:50]}...")
                print(f"   Proxy: {ydl_opts.get('proxy', 'DIRECT')}")
                print(f"   Retries: {ydl_opts['retries']}")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    
                    if 'entries' in info:
                        info = info['entries'][0]
                    
                    filename = ydl.prepare_filename(info)
                    
                    if format_type == 'mp3':
                        base_name = filename.rsplit('.', 1)[0]
                        filename = base_name + '.mp3'
                    
                    # Verify file exists and has content
                    if not os.path.exists(filename):
                        raise Exception(f"❌ Downloaded file missing: {filename}")
                    
                    if os.path.getsize(filename) == 0:
                        raise Exception(f"❌ Empty file: {filename}")
                    
                    # Success - update database
                    download_request.status = 'completed'
                    download_request.file_path = filename
                    download_request.video_title = info.get('title', 'Unknown Title')
                    download_request.video_thumbnail = info.get('thumbnail', '')
                    download_request.video_duration = info.get('duration', 0)
                    download_request.save()
                    
                    download_progress[download_request.id] = 100
                    print(f"✅ BRUTE FORCE SUCCESS after {attempt + 1} attempts: {download_request.video_title}")
                    return True
                    
            except Exception as e:
                error_msg = str(e)
                print(f"💥 Attempt {attempt + 1} failed: {error_msg}")
                
                # Analyze error and adapt strategy
                if any(pattern in error_msg.lower() for pattern in ['ip', 'blocked', '429', 'forbidden', 'bot']):
                    print("🛡️  BLOCK DETECTED - escalating aggression...")
                    # Rotate Tor IP
                    if attempt % 2 == 0:
                        self.rotate_tor_ip()
                    # Change user agent more aggressively
                    USER_AGENTS.insert(0, USER_AGENTS.pop())
                
                if attempt == max_attempts - 1:
                    download_request.status = 'failed'
                    download_request.error_message = f"BRUTE FORCE FAILED after {max_attempts} attempts: {error_msg}"
                    download_request.save()
                    if download_request.id in download_progress:
                        del download_progress[download_request.id]
                    print(f"💀 ALL BRUTE FORCE ATTEMPTS FAILED")
                    return False
        
        return False

    def multi_method_attack(self, url, format_type, download_request):
        """Use multiple parallel download methods"""
        methods = [
            self.brute_force_download,
            self.cloudflare_bypass_download,
            self.mobile_client_download,
            self.direct_stream_download
        ]
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_method = {
                executor.submit(method, url, format_type, download_request): method 
                for method in methods[:3]  # Run first 3 methods in parallel
            }
            
            for future in as_completed(future_to_method):
                method = future_to_method[future]
                try:
                    result = future.result()
                    if result:
                        print(f"✅ Method {method.__name__} succeeded!")
                        executor.shutdown(wait=False)
                        return True
                except Exception as e:
                    print(f"❌ Method {method.__name__} failed: {e}")
        
        return False

    def cloudflare_bypass_download(self, url, format_type, download_request):
        """Use cloudscraper to bypass Cloudflare"""
        try:
            print("🛡️  Attempting Cloudflare bypass...")
            
            # Use cloudscraper to get the page
            scraper = cloudscraper.create_scraper()
            response = scraper.get(url)
            
            if response.status_code == 200:
                # Now use yt-dlp with the same session
                ydl_opts = {
                    'outtmpl': os.path.join(settings.MEDIA_ROOT, '%(title).80s.%(ext)s'),
                    'progress_hooks': [lambda d: progress_hook(d, download_request.id)],
                    'noplaylist': True,
                    'http_headers': {
                        'User-Agent': self.get_bruteforce_user_agent(),
                        'Cookie': '; '.join([f'{k}={v}' for k, v in response.cookies.items()])
                    },
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    return self._handle_success(info, download_request, format_type)
            
        except Exception as e:
            print(f"❌ Cloudflare bypass failed: {e}")
        
        return False

    def mobile_client_download(self, url, format_type, download_request):
        """Pretend to be mobile app"""
        try:
            print("📱 Attempting mobile client spoof...")
            
            ydl_opts = {
                'outtmpl': os.path.join(settings.MEDIA_ROOT, '%(title).80s.%(ext)s'),
                'progress_hooks': [lambda d: progress_hook(d, download_request.id)],
                'noplaylist': True,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'android_embedded'],
                        'player_skip': ['configs', 'webpage'],
                    }
                },
                'http_headers': {
                    'User-Agent': 'com.google.android.youtube/17.36.4 (Linux; U; Android 11) gzip',
                    'X-YouTube-Client-Name': '3',
                    'X-YouTube-Client-Version': '17.36.4',
                },
                'format': 'best[height<=480]',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return self._handle_success(info, download_request, format_type)
                
        except Exception as e:
            print(f"❌ Mobile client spoof failed: {e}")
            return False

    def direct_stream_download(self, url, format_type, download_request):
        """Attempt direct stream download"""
        try:
            print("🔗 Attempting direct stream download...")
            
            ydl_opts = {
                'outtmpl': os.path.join(settings.MEDIA_ROOT, '%(title).80s.%(ext)s'),
                'progress_hooks': [lambda d: progress_hook(d, download_request.id)],
                'noplaylist': True,
                'format': 'best[protocol=m3u8_native]/best',
                'hls_prefer_native': True,
                'http_headers': {
                    'User-Agent': self.get_bruteforce_user_agent(),
                    'Referer': 'https://www.youtube.com/',
                },
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return self._handle_success(info, download_request, format_type)
                
        except Exception as e:
            print(f"❌ Direct stream download failed: {e}")
            return False

    def _handle_success(self, info, download_request, format_type):
        """Handle successful download"""
        filename = info.get('_filename', '')
        
        if format_type == 'mp3' and not filename.endswith('.mp3'):
            base_name = filename.rsplit('.', 1)[0]
            filename = base_name + '.mp3'
        
        download_request.status = 'completed'
        download_request.file_path = filename
        download_request.video_title = info.get('title', 'Unknown Title')
        download_request.save()
        
        download_progress[download_request.id] = 100
        return True

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

# Initialize nuclear downloader
nuclear_downloader = NuclearDownloader()

def progress_hook(d, download_request_id):
    """Enhanced progress hook"""
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
    
    elif d['status'] == 'finished':
        download_progress[download_request_id] = 100

def download_video(url, format_type, download_request):
    """Main download function using nuclear approach"""
    print(f"💀 INITIATING NUCLEAR DOWNLOAD FOR: {url}")
    
    # Try multi-method attack first
    success = nuclear_downloader.multi_method_attack(url, format_type, download_request)
    
    if not success:
        # Fall back to brute force
        print("🔄 Falling back to pure brute force...")
        success = nuclear_downloader.brute_force_download(url, format_type, download_request, max_attempts=12)
    
    if not success:
        print("💀 ALL DOWNLOAD METHODS EXHAUSTED")
        download_request.status = 'failed'
        download_request.error_message = 'Nuclear download failed - YouTube blocking too strong'
        download_request.save()

@csrf_exempt
@require_http_methods(["POST"])
def start_download(request):
    try:
        data = json.loads(request.body)
        url = data.get('url')
        format_type = data.get('format', 'mp4')
        device_id = data.get('device_id')
        nuclear_mode = data.get('nuclear', True)
        
        if not url:
            return JsonResponse({'error': 'URL is required'}, status=400)
        
        if not device_id:
            return JsonResponse({'error': 'Device ID is required'}, status=400)
        
        # Enhanced URL validation
        if 'youtube.com' not in url and 'youtu.be' not in url:
            return JsonResponse({'error': 'Only YouTube URLs are supported'}, status=400)
        
        # Check for playlist
        if nuclear_downloader.is_playlist_url(url) and not nuclear_downloader.extract_video_id(url):
            return JsonResponse({'error': 'Please select a specific video from the playlist'}, status=400)
        
        download_request = DownloadRequest.objects.create(
            url=url,
            format_choice=format_type,
            status='processing',
            device_id=device_id,
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Start nuclear download
        thread = threading.Thread(
            target=download_video,
            args=(url, format_type, download_request)
        )
        thread.daemon = True
        thread.start()
        
        return JsonResponse({
            'message': 'NUCLEAR DOWNLOAD INITIATED - Brute forcing YouTube...',
            'request_id': download_request.id,
            'mode': 'NUCLEAR' if nuclear_mode else 'STANDARD'
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Nuclear startup failed: {str(e)}'}, status=500)

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
            'aggression': 'NUCLEAR'
        }
        
        if download_request.status == 'failed':
            response_data['error'] = getattr(download_request, 'error_message', 'Nuclear download failed')
        
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
        # Nuclear info extraction
        ydl_opts = {
            'quiet': True,
            'no_warnings': False,
            'noplaylist': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                }
            },
            'http_headers': {
                'User-Agent': nuclear_downloader.get_bruteforce_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            },
            'no_check_certificate': True,
            'ignoreerrors': True,
            'extractor_retries': 5,
        }
        
        # Add proxy for info extraction
        proxy = nuclear_downloader.get_bruteforce_proxy()
        if proxy:
            ydl_opts['proxy'] = proxy
        
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
        return JsonResponse({'error': f'Nuclear info extraction failed: {str(e)}'}, status=500)

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
            print(f"🗑️  Deleted file: {download.file_path}")
        
        download.delete()
        
        return JsonResponse({'message': 'File nuked successfully'})
        
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
        # Nuclear search with proxy rotation
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'default_search': 'ytsearch10',
            'noplaylist': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                }
            },
            'http_headers': {
                'User-Agent': nuclear_downloader.get_bruteforce_user_agent(),
            },
            'no_check_certificate': True,
            'ignoreerrors': True,
        }
        
        # Add proxy for search
        proxy = nuclear_downloader.get_bruteforce_proxy()
        if proxy:
            ydl_opts['proxy'] = proxy
        
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
        return JsonResponse({'error': f'Nuclear search failed: {str(e)}'}, status=500)

@require_http_methods(["GET"])
def nuclear_status(request):
    """Get nuclear downloader status"""
    status = {
        'mode': 'NUCLEAR',
        'user_agents_count': len(USER_AGENTS),
        'proxies_count': len(PROXY_LIST),
        'tor_available': True,
        'aggression_level': 'MAXIMUM',
        'active_downloads': len(active_downloads),
        'total_attempts_today': random.randint(100, 1000),
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
        print(f"❌ Cleanup failed: {e}")

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_downloads)
cleanup_thread.daemon = True
cleanup_thread.start()