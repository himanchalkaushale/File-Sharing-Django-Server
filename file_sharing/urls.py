from django.urls import path, re_path
from . import views

app_name = 'file_sharing'

urlpatterns = [
    # Main pages
    path('', views.home, name='home'),
    path('files/', views.file_list, name='file_list'),
    path('about/', views.about, name='about'),
    path('stats/', views.stats, name='stats'),
    
    # File operations
    path('download/<uuid:unique_id>/', views.download_file, name='download_file'),
    path('delete/<uuid:unique_id>/', views.delete_file, name='delete_file'),
    
    # Short link operations
    path('share/create/', views.create_short_link, name='create_short_link'),
    path('share/<str:code>/', views.resolve_short_link, name='resolve_short_link'),
    # Redirect /share/create/share/<code>/ to /share/<code>/
    re_path(r'^share/create/share/(?P<code>[^/]+)/$', views.redirect_to_short_link),
    
    # API endpoints
    path('api/upload/', views.api_upload, name='api_upload'),
    path('api/files/', views.api_file_list, name='api_file_list'),
    path('api/chunked-upload/', views.chunked_upload, name='chunked_upload'),
    path('api/upload-progress/', views.upload_progress, name='upload_progress'),
] 