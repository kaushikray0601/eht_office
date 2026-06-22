from django import forms

from eht.models import ProjectData


class SourceModelUploadForm(forms.Form):
    project = forms.ModelChoiceField(queryset=ProjectData.objects.order_by("proj_id"))
    source_file = forms.FileField(help_text="Upload an IFC, IDF, PCF, or other source model file.")
    display_name = forms.CharField(max_length=255, required=False)
    source_system = forms.CharField(max_length=80, required=False)

