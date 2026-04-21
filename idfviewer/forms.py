from django import forms
from eht.models import ProjectData

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all'}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)] if data else []
        return result

class PipelineUploadForm(forms.Form):
    project = forms.ModelChoiceField(
        queryset=ProjectData.objects.all(),
        label="Select Project",
        required=True,
        empty_label="--- Select Project ---",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all'
        })
    )
    
    idf_files = MultipleFileField(
        label="Select Pipeline File(s)",
        help_text="Upload one or more .idf or .pcf files",
        required=False,
    )

    idf_directory = MultipleFileField(
        label="Or Select a Folder",
        help_text="Upload a folder containing .idf or .pcf files",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['idf_directory'].widget.attrs.update({
            'webkitdirectory': True,
            'directory': True,
        })
        
    def clean(self):
        cleaned_data = super().clean()
        f1 = cleaned_data.get('idf_files') or []
        f2 = cleaned_data.get('idf_directory') or []
        
        if not f1 and not f2:
            raise forms.ValidationError("Please select file(s) or a folder to upload.")
            
        return cleaned_data


IDFUploadForm = PipelineUploadForm
