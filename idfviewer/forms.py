from django import forms


class IDFUploadForm(forms.Form):
    idf_file = forms.FileField(
        label="Select IDF file",
        help_text="Upload a plain-text plant/Isogen IDF file"
    )