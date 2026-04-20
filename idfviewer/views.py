from django.shortcuts import render
from .forms import IDFUploadForm
from .parser import parse_idf_text
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
            # If it decodes but still contains too many nulls, try next
            if text.count("\x00") > 10:
                continue
            return text
        except UnicodeDecodeError:
            continue

    # Final fallback
    return raw.decode("latin-1", errors="replace")


def upload_idf_view(request):
    if request.method == "POST":
        form = IDFUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data["idf_file"]

            raw = uploaded_file.read()
            text = decode_idf_bytes(raw)

            scene = parse_idf_text(text)

            return render(
                request,
                "idfviewer/viewer.html",
                {
                    "scene": scene,
                    "filename": uploaded_file.name,
                },
            )
    else:
        form = IDFUploadForm()

    return render(request, "idfviewer/upload.html", {"form": form})