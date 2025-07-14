from django.db import models
from django.utils import timezone
import os
import uuid
import hashlib

def get_file_path(instance, filename):
    """Generate unique file path for uploaded files"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads', filename)

class FileUpload(models.Model):
    """Model to store uploaded file information"""
    file = models.FileField(upload_to=get_file_path, max_length=500)
    filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    file_type = models.CharField(max_length=100)
    uploaded_at = models.DateTimeField(default=timezone.now)
    download_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    md5_hash = models.CharField(max_length=32, blank=True, null=True, help_text="MD5 hash for file integrity")
    sha256_hash = models.CharField(max_length=64, blank=True, null=True, help_text="SHA256 hash for file integrity")
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'File Upload'
        verbose_name_plural = 'File Uploads'
    
    def __str__(self):
        return f"{self.filename} ({self.file_size} bytes)"
    
    def get_file_size_mb(self):
        """Return file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    def get_file_size_kb(self):
        """Return file size in KB"""
        return round(self.file_size / 1024, 2)
    
    def get_file_extension(self):
        """Return file extension"""
        return os.path.splitext(self.filename)[1].lower()
    
    def increment_download_count(self):
        """Increment download count"""
        self.download_count += 1
        self.save(update_fields=['download_count'])
    
    def calculate_hashes(self):
        """Calculate MD5 and SHA256 hashes for the file"""
        if not self.file:
            return None, None
        
        md5_hash = hashlib.md5()
        sha256_hash = hashlib.sha256()
        
        try:
            with open(self.file.path, 'rb') as f:
                while True:
                    chunk = f.read(8192)  # Read in 8KB chunks
                    if not chunk:
                        break
                    md5_hash.update(chunk)
                    sha256_hash.update(chunk)
            
            return md5_hash.hexdigest(), sha256_hash.hexdigest()
        except Exception as e:
            print(f"Error calculating hashes: {e}")
            return None, None
    
    def verify_file_integrity(self):
        """Verify file integrity by recalculating hashes"""
        if not self.md5_hash or not self.sha256_hash:
            return False
        
        current_md5, current_sha256 = self.calculate_hashes()
        return (current_md5 == self.md5_hash and current_sha256 == self.sha256_hash)

class ShortLink(models.Model):
    code = models.CharField(max_length=32, unique=True, help_text="Custom short code, e.g. 'myfile'")
    target_url = models.URLField(help_text='The actual file download or external link')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code
