from django import forms

from .project_gateway import project_options_for_user, validate_project_id


class SourceModelUploadForm(forms.Form):
    project = forms.ChoiceField(choices=[])
    source_file = forms.FileField(help_text="Upload an IFC, IDF, PCF, or other source model file.")
    display_name = forms.CharField(max_length=255, required=False)
    source_system = forms.CharField(max_length=80, required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["project"].choices = [
            (project.project_id, project.label)
            for project in project_options_for_user(user)
        ]

    def clean_project(self):
        project_id = validate_project_id(self.cleaned_data["project"], self.user)
        if not project_id:
            raise forms.ValidationError("Select a valid project.")
        return project_id
