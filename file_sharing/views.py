from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, Http404, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Sum, Count
import os
import mimetypes
from .models import FileUpload, ShortLink
from .forms import FileUploadForm, ShortLinkForm
import json
import tempfile
import shutil
import socket
from urllib.parse import urlparse
import re
import requests

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def home(request):
    """Home page with file upload form and recent files"""
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file_upload = form.save(commit=False)
            file_upload.file_size = request.FILES['file'].size
            file_upload.file_type = request.FILES['file'].content_type or 'application/octet-stream'
            file_upload.save()
            
            # Calculate hashes for file integrity
            md5_hash, sha256_hash = file_upload.calculate_hashes()
            if md5_hash and sha256_hash:
                file_upload.md5_hash = md5_hash
                file_upload.sha256_hash = sha256_hash
                file_upload.save(update_fields=['md5_hash', 'sha256_hash'])
                messages.success(request, f'File "{file_upload.filename}" uploaded successfully with integrity verification!')
            else:
                messages.warning(request, f'File "{file_upload.filename}" uploaded but hash calculation failed.')
            
            return redirect('file_sharing:home')
        else:
            messages.error(request, 'Error uploading file. Please try again.')
    else:
        form = FileUploadForm()
    
    # Get recent files
    recent_files = FileUpload.objects.filter(is_active=True).order_by('-uploaded_at')[:10]
    
    context = {
        'form': form,
        'recent_files': recent_files,
        'local_ip': get_local_ip(),
    }
    return render(request, 'file_sharing/home.html', context)

def file_list(request):
    """Display all uploaded files, only active files."""
    search_query = request.GET.get('search', '')
    files = FileUpload.objects.filter(is_active=True)
    
    if search_query:
        files = files.filter(
            Q(filename__icontains=search_query) |
            Q(file_type__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(files, 20)  # Show 20 files per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Calculate total downloads
    total_downloads = files.aggregate(Sum('download_count'))['download_count__sum'] or 0
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_files': files.count(),
        'total_downloads': total_downloads,
    }
    return render(request, 'file_sharing/file_list.html', context)

def download_file(request, unique_id):
    """Download a file by its unique ID"""
    try:
        file_upload = get_object_or_404(FileUpload, unique_id=unique_id, is_active=True)
        
        # Check if file exists
        if not os.path.exists(file_upload.file.path):
            raise Http404("File not found")
        
        # Verify file integrity if hashes are available
        if file_upload.md5_hash and file_upload.sha256_hash:
            if not file_upload.verify_file_integrity():
                messages.error(request, 'File integrity check failed. The file may be corrupted.')
                return redirect('file_sharing:file_list')
        
        # Increment download count
        file_upload.increment_download_count()
        
        # Prepare response using FileResponse for efficient streaming
        response = FileResponse(open(file_upload.file.path, 'rb'), content_type=file_upload.file_type)
        response['Content-Disposition'] = f'attachment; filename="{file_upload.filename}"'
        response['Content-Length'] = file_upload.file_size
        
        # Add hash information to headers for client verification
        if file_upload.md5_hash:
            response['X-File-MD5'] = file_upload.md5_hash
        if file_upload.sha256_hash:
            response['X-File-SHA256'] = file_upload.sha256_hash
        
        return response
        
    except Exception as e:
        messages.error(request, f'Error downloading file: {str(e)}')
        return redirect('file_sharing:file_list')

def delete_file(request, unique_id):
    """Delete a file by unique_id, only active files."""
    if request.method == 'POST':
        try:
            file_upload = get_object_or_404(FileUpload, unique_id=unique_id, is_active=True)
            # Delete the physical file
            if os.path.exists(file_upload.file.path):
                os.remove(file_upload.file.path)
            # Delete all short links pointing to this file's download URL
            download_url = f"/download/{file_upload.unique_id}/"
            ShortLink.objects.filter(target_url__icontains=download_url).delete()
            # Delete the database record
            filename = file_upload.filename
            file_upload.delete()
            messages.success(request, f'File "{filename}" and related short links deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting file: {str(e)}')
    return redirect('file_sharing:file_list')

@csrf_exempt
@require_http_methods(["POST"])
def api_upload(request):
    """API endpoint for file upload (for mobile apps)"""
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        uploaded_file = request.FILES['file']
        
        # Create file upload object
        file_upload = FileUpload(
            file=uploaded_file,
            filename=uploaded_file.name,
            file_size=uploaded_file.size,
            file_type=uploaded_file.content_type or 'application/octet-stream'
        )
        file_upload.save()
        
        # Calculate hashes for file integrity
        md5_hash, sha256_hash = file_upload.calculate_hashes()
        if md5_hash and sha256_hash:
            file_upload.md5_hash = md5_hash
            file_upload.sha256_hash = sha256_hash
            file_upload.save(update_fields=['md5_hash', 'sha256_hash'])
        
        return JsonResponse({
            'success': True,
            'file_id': str(file_upload.unique_id),
            'filename': file_upload.filename,
            'file_size': file_upload.file_size,
            'download_url': request.build_absolute_uri(f'/download/{file_upload.unique_id}/'),
            'md5_hash': md5_hash,
            'sha256_hash': sha256_hash
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def api_file_list(request):
    """API endpoint to get list of files"""
    try:
        files = FileUpload.objects.filter(is_active=True).order_by('-uploaded_at')
        file_list = []
        
        for file_upload in files:
            file_list.append({
                'id': str(file_upload.unique_id),
                'filename': file_upload.filename,
                'file_size': file_upload.file_size,
                'file_type': file_upload.file_type,
                'uploaded_at': file_upload.uploaded_at.isoformat(),
                'download_count': file_upload.download_count,
                'download_url': request.build_absolute_uri(f'/download/{file_upload.unique_id}/')
            })
        
        return JsonResponse({'files': file_list})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def about(request):
    """About page with information about the file sharing service"""
    return render(request, 'file_sharing/about.html')

def stats(request):
    """Statistics page showing file sharing statistics"""
    total_files = FileUpload.objects.filter(is_active=True).count()
    total_downloads = FileUpload.objects.filter(is_active=True).aggregate(
        total=Sum('download_count')
    )['total'] or 0
    total_size = FileUpload.objects.filter(is_active=True).aggregate(
        total=Sum('file_size')
    )['total'] or 0
    
    # File type statistics with percentages
    file_types = FileUpload.objects.filter(is_active=True).values('file_type').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Calculate percentages for each file type
    for file_type in file_types:
        if total_files > 0:
            file_type['percentage'] = round((file_type['count'] / total_files) * 100, 1)
        else:
            file_type['percentage'] = 0
    
    # Calculate average downloads per file
    avg_downloads_per_file = round(total_downloads / total_files, 1) if total_files > 0 else 0
    
    context = {
        'total_files': total_files,
        'total_downloads': total_downloads,
        'total_size_mb': round(total_size / (1024 * 1024), 2),
        'file_types': file_types,
        'avg_downloads_per_file': avg_downloads_per_file,
    }
    return render(request, 'file_sharing/stats.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def chunked_upload(request):
    """Handle chunked file uploads with progress tracking"""
    try:
        # Get upload parameters
        file_id = request.POST.get('file_id')
        chunk_number = int(request.POST.get('chunk_number', 0))
        total_chunks = int(request.POST.get('total_chunks', 1))
        filename = request.POST.get('filename')
        file_size = int(request.POST.get('file_size', 0))
        file_type = request.POST.get('file_type', 'application/octet-stream')
        
        if 'chunk' not in request.FILES:
            return JsonResponse({'error': 'No chunk data provided'}, status=400)
        
        chunk_data = request.FILES['chunk']
        
        # Create temporary directory for chunks
        temp_dir = os.path.join(tempfile.gettempdir(), 'file_sharing_chunks', file_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Save chunk
        chunk_path = os.path.join(temp_dir, f'chunk_{chunk_number}')
        with open(chunk_path, 'wb') as f:
            for chunk in chunk_data.chunks():
                f.write(chunk)
        
        # Check if all chunks are uploaded
        if chunk_number == total_chunks - 1:
            # Combine all chunks
            final_path = os.path.join(temp_dir, 'final_file')
            with open(final_path, 'wb') as outfile:
                for i in range(total_chunks):
                    chunk_path = os.path.join(temp_dir, f'chunk_{i}')
                    if os.path.exists(chunk_path):
                        with open(chunk_path, 'rb') as infile:
                            outfile.write(infile.read())
                        os.remove(chunk_path)  # Clean up chunk
            
            # Create FileUpload object
            with open(final_path, 'rb') as f:
                file_upload = FileUpload(
                    filename=filename,
                    file_size=file_size,
                    file_type=file_type
                )
                file_upload.file.save(filename, f, save=False)
                file_upload.save()
            
            # Calculate hashes for file integrity
            md5_hash, sha256_hash = file_upload.calculate_hashes()
            if md5_hash and sha256_hash:
                file_upload.md5_hash = md5_hash
                file_upload.sha256_hash = sha256_hash
                file_upload.save(update_fields=['md5_hash', 'sha256_hash'])
            
            # Clean up temporary directory
            shutil.rmtree(temp_dir)
            
            return JsonResponse({
                'success': True,
                'file_id': str(file_upload.unique_id),
                'filename': file_upload.filename,
                'file_size': file_upload.file_size,
                'download_url': request.build_absolute_uri(f'/download/{file_upload.unique_id}/'),
                'md5_hash': md5_hash,
                'sha256_hash': sha256_hash,
                'message': 'File uploaded successfully with integrity verification!'
            })
        
        # Return progress for incomplete upload
        return JsonResponse({
            'success': True,
            'chunk_number': chunk_number,
            'total_chunks': total_chunks,
            'progress': round((chunk_number + 1) / total_chunks * 100, 2),
            'message': f'Chunk {chunk_number + 1} of {total_chunks} uploaded'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def upload_progress(request):
    """Get upload progress for a specific file"""
    try:
        file_id = request.POST.get('file_id')
        temp_dir = os.path.join(tempfile.gettempdir(), 'file_sharing_chunks', file_id)
        
        if not os.path.exists(temp_dir):
            return JsonResponse({'error': 'Upload session not found'}, status=404)
        
        # Count uploaded chunks
        uploaded_chunks = len([f for f in os.listdir(temp_dir) if f.startswith('chunk_')])
        
        # Try to get total chunks from metadata file
        metadata_file = os.path.join(temp_dir, 'metadata.json')
        total_chunks = 1
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                total_chunks = metadata.get('total_chunks', 1)
        
        progress = round(uploaded_chunks / total_chunks * 100, 2) if total_chunks > 0 else 0
        
        return JsonResponse({
            'uploaded_chunks': uploaded_chunks,
            'total_chunks': total_chunks,
            'progress': progress
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def create_short_link(request):
    """View to create a custom short link"""
    if request.method == 'POST':
        form = ShortLinkForm(request.POST)
        if form.is_valid():
            short_link = form.save(commit=False)
            short_link.save()
            return render(request, 'file_sharing/shortlink_success.html', {'short_link': short_link})
    else:
        form = ShortLinkForm()
    return render(request, 'file_sharing/create_shortlink.html', {'form': form, 'local_ip': get_local_ip()})

def resolve_short_link(request, code):
    """Redirect to the target URL for a given short code, or show a message if the file is deleted/missing or the target is unreachable."""
    short_link = get_object_or_404(ShortLink, code=code)
    parsed = urlparse(short_link.target_url)
    # 1. If the target is a download link to a missing file
    if parsed.path.startswith('/download/'):
        match = re.match(r'/download/([\w-]+)/', parsed.path)
        if match:
            unique_id = match.group(1)
            file_qs = FileUpload.objects.filter(unique_id=unique_id, is_active=True)
            if not file_qs.exists():
                return render(request, 'file_sharing/file_deleted.html', {'code': code})
    # 2. If the target is unreachable (404 or connection error)
    try:
        # Build absolute URL if needed
        if short_link.target_url.startswith('/'):
            # Local path, build full URL
            base_url = request.build_absolute_uri('/')[:-1]
            check_url = base_url + short_link.target_url
        else:
            check_url = short_link.target_url
        resp = requests.head(check_url, allow_redirects=True, timeout=3)
        if resp.status_code == 404:
            return render(request, 'file_sharing/file_deleted.html', {'code': code})
    except Exception:
        return render(request, 'file_sharing/file_deleted.html', {'code': code})
    return redirect(short_link.target_url)

def redirect_to_short_link(request, code):
    """Redirect /share/create/share/<code>/ to /share/<code>/ for mistyped or legacy links."""
    return redirect('file_sharing:resolve_short_link', code=code)
