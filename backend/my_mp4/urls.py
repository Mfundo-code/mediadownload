from django.urls import path
from . import views

urlpatterns = [
    path('download/', views.start_download, name='start_download'),
    path('status/<int:request_id>/', views.check_status, name='check_status'),
    path('download-file/', views.download_file, name='download_file'),
    path('play-file/', views.play_file, name='play_file'),
    path('video-info/', views.get_video_info, name='get_video_info'),
    path('downloads/history/', views.get_download_history, name='get_download_history'),
    path('downloads/delete/<int:download_id>/', views.delete_download, name='delete_download'),
]