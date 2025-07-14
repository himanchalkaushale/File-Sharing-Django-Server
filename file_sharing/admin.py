from django.contrib import admin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path
from django.http import HttpResponseRedirect, HttpResponse, FileResponse
from django.utils.html import format_html
from django.core.files.base import ContentFile
from django.db import models
import os
from .models import FileUpload
from django.db.models import Sum

@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    list_display = ('filename', 'file_size_mb', 'file_type', 'uploaded_at', 'download_count', 'integrity_status', 'is_active', 'admin_actions')
    list_filter = ('file_type', 'uploaded_at', 'is_active')
    search_fields = ('filename', 'unique_id', 'md5_hash', 'sha256_hash')
    readonly_fields = ('unique_id', 'uploaded_at', 'download_count', 'display_file_size', 'file_type', 'md5_hash', 'sha256_hash', 'integrity_status')
    list_per_page = 25
    
    fieldsets = (
        ('File Information', {
            'fields': ('file', 'filename', 'display_file_size', 'file_type')
        }),
        ('Integrity Verification', {
            'fields': ('md5_hash', 'sha256_hash', 'integrity_status'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('unique_id', 'uploaded_at', 'download_count', 'is_active')
        }),
    )
    
    def file_size_mb(self, obj):
        return f"{obj.get_file_size_mb()} MB"
    file_size_mb.short_description = 'Size (MB)'
    
    def display_file_size(self, obj):
        """Format file size for display in admin forms"""
        size = obj.file_size
        if size is None:
            return "0 Bytes"
        if size < 1024:
            return f"{size} Bytes"
        elif size < 1024**2:
            return f"{size/1024:.2f} KB"
        elif size < 1024**3:
            return f"{size/1024**2:.2f} MB"
        else:
            return f"{size/1024**3:.2f} GB"
    display_file_size.short_description = 'File size'
    
    def integrity_status(self, obj):
        """Display file integrity status with icons"""
        if not obj.md5_hash or not obj.sha256_hash:
            return format_html('<span class="integrity-no-hash"><i class="fas fa-exclamation-triangle"></i> No Hash</span>')
        
        if obj.verify_file_integrity():
            return format_html('<span class="integrity-verified"><i class="fas fa-check-circle"></i> Verified</span>')
        else:
            return format_html('<span class="integrity-corrupted"><i class="fas fa-times-circle"></i> Corrupted</span>')
    integrity_status.short_description = 'Integrity'
    
    def admin_actions(self, obj):
        """Display action buttons with icons in a single row"""
        return format_html(
            '<div class="admin-actions-buttons">'
            '<a class="button" href="{}" title="Edit"><i class="fas fa-edit"></i></a> '
            '<a class="button" href="{}" title="Replace File"><i class="fas fa-exchange-alt"></i></a> '
            '<a class="button" href="{}" title="Download"><i class="fas fa-download"></i></a> '
            '<a class="button" href="{}" title="Verify Integrity"><i class="fas fa-shield-alt"></i></a>'
            '</div>',
            f'/admin/file_sharing/fileupload/{obj.id}/change/',
            f'/admin/file_sharing/fileupload/{obj.id}/replace_file/',
            f'/admin/file_sharing/fileupload/{obj.id}/download/',
            f'/admin/file_sharing/fileupload/{obj.id}/verify_integrity/'
        )
    admin_actions.short_description = 'Actions'
    
    def has_add_permission(self, request):
        return True  # Allow manual file creation in admin
    
    actions = [
        'mark_inactive', 
        'mark_active', 
        'reset_download_count',
        'delete_files',
        'duplicate_files',
        'export_file_info',
        'verify_integrity',
        'recalculate_hashes'
    ]
    
    def mark_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} files marked as inactive.')
    mark_inactive.short_description = "Mark selected files as inactive"
    
    def mark_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} files marked as active.')
    mark_active.short_description = "Mark selected files as active"
    
    def reset_download_count(self, request, queryset):
        updated = queryset.update(download_count=0)
        self.message_user(request, f'Download count reset for {updated} files.')
    reset_download_count.short_description = "Reset download count to 0"
    
    def delete_files(self, request, queryset):
        count = queryset.count()
        for file_obj in queryset:
            # Delete the actual file from storage
            if file_obj.file and os.path.exists(file_obj.file.path):
                os.remove(file_obj.file.path)
        queryset.delete()
        self.message_user(request, f'{count} files deleted successfully.')
    delete_files.short_description = "Delete selected files (permanent)"
    
    def duplicate_files(self, request, queryset):
        duplicated_count = 0
        for file_obj in queryset:
            # Create a copy of the file
            new_filename = f"copy_{file_obj.filename}"
            new_file_obj = FileUpload.objects.create(
                filename=new_filename,
                file_size=file_obj.file_size,
                file_type=file_obj.file_type,
                is_active=file_obj.is_active
            )
            
            # Copy the actual file
            if file_obj.file and os.path.exists(file_obj.file.path):
                with open(file_obj.file.path, 'rb') as original_file:
                    new_file_obj.file.save(
                        os.path.basename(file_obj.file.name),
                        ContentFile(original_file.read())
                    )
                duplicated_count += 1
        
        self.message_user(request, f'{duplicated_count} files duplicated successfully.')
    duplicate_files.short_description = "Duplicate selected files"
    
    def export_file_info(self, request, queryset):
        """Export file information as CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="file_info.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Filename', 'Size (MB)', 'Type', 'Uploaded', 'Downloads', 'Active', 'Unique ID', 'MD5 Hash', 'SHA256 Hash', 'Integrity Status'])
        
        for file_obj in queryset:
            integrity_status = 'Unknown'
            if file_obj.md5_hash and file_obj.sha256_hash:
                integrity_status = 'Verified' if file_obj.verify_file_integrity() else 'Corrupted'
            else:
                integrity_status = 'No Hash'
            
            writer.writerow([
                file_obj.filename,
                file_obj.get_file_size_mb(),
                file_obj.file_type,
                file_obj.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
                file_obj.download_count,
                'Yes' if file_obj.is_active else 'No',
                file_obj.unique_id,
                file_obj.md5_hash or 'N/A',
                file_obj.sha256_hash or 'N/A',
                integrity_status
            ])
        
        return response
    export_file_info.short_description = "Export file information as CSV"
    
    def verify_integrity(self, request, queryset):
        """Verify integrity of selected files"""
        verified_count = 0
        corrupted_count = 0
        no_hash_count = 0
        
        for file_obj in queryset:
            if not file_obj.md5_hash or not file_obj.sha256_hash:
                no_hash_count += 1
            elif file_obj.verify_file_integrity():
                verified_count += 1
            else:
                corrupted_count += 1
        
        message_parts = []
        if verified_count > 0:
            message_parts.append(f'{verified_count} files verified')
        if corrupted_count > 0:
            message_parts.append(f'{corrupted_count} files corrupted')
        if no_hash_count > 0:
            message_parts.append(f'{no_hash_count} files without hashes')
        
        self.message_user(request, f'Integrity check complete: {", ".join(message_parts)}.')
    verify_integrity.short_description = "Verify file integrity"
    
    def recalculate_hashes(self, request, queryset):
        """Recalculate hashes for selected files"""
        updated_count = 0
        failed_count = 0
        
        for file_obj in queryset:
            try:
                md5_hash, sha256_hash = file_obj.calculate_hashes()
                if md5_hash and sha256_hash:
                    file_obj.md5_hash = md5_hash
                    file_obj.sha256_hash = sha256_hash
                    file_obj.save(update_fields=['md5_hash', 'sha256_hash'])
                    updated_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1
        
        message_parts = []
        if updated_count > 0:
            message_parts.append(f'{updated_count} hashes updated')
        if failed_count > 0:
            message_parts.append(f'{failed_count} failed')
        
        self.message_user(request, f'Hash recalculation complete: {", ".join(message_parts)}.')
    recalculate_hashes.short_description = "Recalculate file hashes"
    
    def get_urls(self):
        """Add custom URLs for file operations"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:file_id>/replace_file/',
                self.admin_site.admin_view(self.replace_file_view),
                name='file_sharing_fileupload_replace_file',
            ),
            path(
                '<int:file_id>/download/',
                self.admin_site.admin_view(self.download_file_view),
                name='file_sharing_fileupload_download',
            ),
            path(
                '<int:file_id>/verify_integrity/',
                self.admin_site.admin_view(self.verify_integrity_view),
                name='file_sharing_fileupload_verify_integrity',
            ),
        ]
        return custom_urls + urls
    
    def replace_file_view(self, request, file_id):
        """Custom view to replace a file"""
        try:
            file_obj = FileUpload.objects.get(id=file_id)
            
            if request.method == 'POST':
                new_file = request.FILES.get('new_file')
                if new_file:
                    # Validate file size (100GB limit)
                    max_size = 100 * 1024 * 1024 * 1024  # 100GB in bytes
                    if new_file.size > max_size:
                        messages.error(request, f'File size exceeds 100GB limit. Current size: {new_file.size / (1024**3):.2f} GB')
                        return HttpResponseRedirect(f'/admin/file_sharing/fileupload/{file_id}/replace_file/')
                    
                    # Delete old file
                    if file_obj.file and os.path.exists(file_obj.file.path):
                        os.remove(file_obj.file.path)
                    
                    # Update with new file
                    file_obj.file = new_file
                    file_obj.filename = new_file.name
                    file_obj.file_size = new_file.size
                    file_obj.file_type = new_file.content_type
                    file_obj.save()
                    
                    # Calculate hashes for the new file
                    md5_hash, sha256_hash = file_obj.calculate_hashes()
                    if md5_hash and sha256_hash:
                        file_obj.md5_hash = md5_hash
                        file_obj.sha256_hash = sha256_hash
                        file_obj.save(update_fields=['md5_hash', 'sha256_hash'])
                        messages.success(request, f'File "{file_obj.filename}" replaced successfully with integrity verification!')
                    else:
                        messages.warning(request, f'File "{file_obj.filename}" replaced but hash calculation failed.')
                    
                    return HttpResponseRedirect(f'/admin/file_sharing/fileupload/{file_id}/change/')
                else:
                    messages.error(request, 'No file was uploaded.')
                    return HttpResponseRedirect(f'/admin/file_sharing/fileupload/{file_id}/replace_file/')
            
            # Show replacement form using custom template
            from django.template.loader import render_to_string
            
            context = {
                'title': f'Replace File: {file_obj.filename}',
                'file_obj': file_obj,
                'opts': self.model._meta,
                'has_view_permission': True,
                'has_add_permission': True,
                'has_change_permission': True,
                'has_delete_permission': True,
            }
            
            html_content = render_to_string('admin/file_sharing/fileupload/replace_file.html', context, request=request)
            return HttpResponse(html_content)
            
        except FileUpload.DoesNotExist:
            messages.error(request, 'File not found.')
            return HttpResponseRedirect('/admin/file_sharing/fileupload/')
    
    def download_file_view(self, request, file_id):
        """Custom view to download a file"""
        try:
            file_obj = FileUpload.objects.get(id=file_id)
            
            if not file_obj.file or not os.path.exists(file_obj.file.path):
                messages.error(request, 'File not found on disk.')
                return HttpResponseRedirect(f'/admin/file_sharing/fileupload/{file_id}/change/')
            
            # Verify file integrity before download
            if file_obj.md5_hash and file_obj.sha256_hash:
                if not file_obj.verify_file_integrity():
                    messages.warning(request, 'File integrity check failed. The file may be corrupted.')
            
            # Increment download count
            file_obj.increment_download_count()
            
            # Prepare response
            response = FileResponse(open(file_obj.file.path, 'rb'), content_type=file_obj.file_type)
            response['Content-Disposition'] = f'attachment; filename="{file_obj.filename}"'
            response['Content-Length'] = file_obj.file_size
            
            # Add hash information to headers
            if file_obj.md5_hash:
                response['X-File-MD5'] = file_obj.md5_hash
            if file_obj.sha256_hash:
                response['X-File-SHA256'] = file_obj.sha256_hash
            
            return response
            
        except FileUpload.DoesNotExist:
            messages.error(request, 'File not found.')
            return HttpResponseRedirect('/admin/file_sharing/fileupload/')
    
    def verify_integrity_view(self, request, file_id):
        """Custom view to verify file integrity"""
        try:
            file_obj = FileUpload.objects.get(id=file_id)
            
            if not file_obj.file or not os.path.exists(file_obj.file.path):
                messages.error(request, 'File not found on disk.')
                return HttpResponseRedirect(f'/admin/file_sharing/fileupload/{file_id}/change/')
            
            # Verify integrity
            if not file_obj.md5_hash or not file_obj.sha256_hash:
                messages.warning(request, 'No hash information available for this file.')
            elif file_obj.verify_file_integrity():
                messages.success(request, 'File integrity verified successfully! ✅')
            else:
                messages.error(request, 'File integrity check failed! The file may be corrupted. ❌')
            
            return HttpResponseRedirect(f'/admin/file_sharing/fileupload/{file_id}/change/')
            
        except FileUpload.DoesNotExist:
            messages.error(request, 'File not found.')
            return HttpResponseRedirect('/admin/file_sharing/fileupload/')
    
    def save_model(self, request, obj, form, change):
        """Override save to handle file size and type updates"""
        if change and 'file' in form.changed_data:
            # Update file size and type when file is changed
            if obj.file:
                obj.file_size = obj.file.size
                obj.file_type = obj.file.content_type
        
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly when editing existing files"""
        if obj:  # Editing existing file
            return self.readonly_fields + ('file_size', 'file_type')
        return self.readonly_fields
    
    def changelist_view(self, request, extra_context=None):
        """Override changelist view to add advanced statistics"""
        
        # Global statistics
        total_files = FileUpload.objects.count()
        active_files = FileUpload.objects.filter(is_active=True).count()
        inactive_files = FileUpload.objects.filter(is_active=False).count()
        total_downloads = FileUpload.objects.aggregate(total=Sum('download_count'))['total'] or 0
        total_size_bytes = FileUpload.objects.aggregate(total=Sum('file_size'))['total'] or 0
        total_size_mb = round(total_size_bytes / (1024 * 1024), 2)
        
        extra_context = extra_context or {}
        extra_context.update({
            'global_total_files': total_files,
            'global_active_files': active_files,
            'global_inactive_files': inactive_files,
            'global_total_downloads': total_downloads,
            'global_total_size_mb': total_size_mb,
        })
        
        return super().changelist_view(request, extra_context)
