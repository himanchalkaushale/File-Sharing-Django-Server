from django import forms
from .models import FileUpload, ShortLink

class FileUploadForm(forms.ModelForm):
    """Form for file upload with validation"""
    
    class Meta:
        model = FileUpload
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '*/*',
                'multiple': False,
            })
        }
    
    def clean_file(self):
        """Validate uploaded file"""
        file = self.cleaned_data.get('file')
        
        if not file:
            raise forms.ValidationError('Please select a file to upload.')
        
        # Check file size (100GB limit)
        if file.size > 107374182400:  # 100GB in bytes
            raise forms.ValidationError('File size must be less than 100GB.')
        
        # Check file name length
        if len(file.name) > 255:
            raise forms.ValidationError('File name is too long.')
        
        # Check for potentially dangerous file extensions
        dangerous_extensions = ['.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js']
        file_extension = file.name.lower().split('.')[-1] if '.' in file.name else ''
        
        if f'.{file_extension}' in dangerous_extensions:
            raise forms.ValidationError('This file type is not allowed for security reasons.')
        
        return file
    
    def save(self, commit=True):
        """Override save to set filename"""
        instance = super().save(commit=False)
        if self.cleaned_data.get('file'):
            instance.filename = self.cleaned_data['file'].name
        if commit:
            instance.save()
        return instance

class ShortLinkForm(forms.ModelForm):
    class Meta:
        model = ShortLink
        fields = ['code', 'target_url']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter custom code (e.g. myfile)'}),
            'target_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Paste the file or P2P link here'}),
        }
    
    def clean_code(self):
        code = self.cleaned_data['code']
        if not code.isalnum():
            raise forms.ValidationError('Code must be alphanumeric (letters and numbers only).')
        return code 