from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import IDFUploadForm
from .parser import parse_multiple_idf_texts
import codecs


def decode_idf_bytes(raw: bytes) -> str:
    """
    Robust decoder for plant IDF files.
    Many exports from PDMS/Isodraft come as UTF-16 LE.
    """
    encodings_to_try = []

    if raw.startswith(codecs.BOM_UTF16_LE) or raw.startswith(codecs.BOM_UTF16_BE):
        encodings_to_try = ["utf-16", "utf-16-le", "utf-16-be", "utf-8-sig", "utf-8"]
    else:
        encodings_to_try = ["utf-8-sig", "utf-8", "utf-16", "utf-16-le", "cp1252", "latin-1"]

    for enc in encodings_to_try:
        try:
            text = raw.decode(enc)
            if text.count("\x00") > 10:
                continue
            return text
        except UnicodeDecodeError:
            continue

    return raw.decode("latin-1", errors="replace")


def upload_idf_view(request):
    if request.method == "POST":
        form = IDFUploadForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.cleaned_data["project"]
            f1 = form.cleaned_data.get('idf_files') or []
            f2 = form.cleaned_data.get('idf_directory') or []
            all_files = f1 + f2

            file_payloads = []
            for uf in all_files:
                # Some browsers prefix directory files with full path
                fname = uf.name.split('/')[-1]
                if not fname.lower().endswith('.idf'):
                    continue
                raw = uf.read()
                text = decode_idf_bytes(raw)
                file_payloads.append((fname, text))

            if not file_payloads:
                messages.error(request, "No valid .idf files found in upload.")
                return render(request, "idfviewer/upload.html", {"form": form})

            # Process through the upgraded parser which populates the DB and returns the unified scene
            scene = parse_multiple_idf_texts(file_payloads, project)

            return render(
                request,
                "idfviewer/viewer.html",
                {
                    "scene": scene,
                    "filename": f"Batch: {len(file_payloads)} files",
                    "project": project
                },
            )
    else:
        form = IDFUploadForm()

    return render(request, "idfviewer/upload.html", {"form": form})