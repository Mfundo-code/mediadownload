from django.db import models

class DownloadRequest(models.Model):
    url = models.URLField(max_length=500)
    format_choice = models.CharField(max_length=10, default='mp4')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')
    file_path = models.CharField(max_length=500, blank=True, null=True)
    video_title = models.CharField(max_length=500, blank=True, null=True)
    video_thumbnail = models.URLField(max_length=500, blank=True, null=True)
    video_duration = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.url} - {self.status}"