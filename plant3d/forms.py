from django import forms

from eht.models import ProjectData


class SourceModelUploadForm(forms.Form):
    project = forms.ModelChoiceField(queryset=ProjectData.objects.order_by("proj_id"))
    source_file = forms.FileField(help_text="Upload an IFC, IDF, PCF, or other source model file.")
    display_name = forms.CharField(max_length=255, required=False)
    source_system = forms.CharField(max_length=80, required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None and getattr(user, "is_authenticated", False):
            from .access import accessible_project_ids

            self.fields["project"].queryset = ProjectData.objects.filter(
                proj_id__in=accessible_project_ids(user)
            ).order_by("proj_id")
