from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import PipelineUploadForm
from .parser import parse_multiple_idf_texts
from .pcf_parser import parse_multiple_pcf_texts
import codecs
import re


def decode_pipeline_bytes(raw: bytes) -> str:
    """
    Robust decoder for plant pipeline files.
    IDF files are often UTF-16 LE, while PCF is usually plain text.
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


def detect_pipeline_format(filename: str, text: str) -> str | None:
    lower_name = filename.lower()
    if lower_name.endswith(".idf"):
        return "IDF"
    if lower_name.endswith(".pcf"):
        return "PCF"

    head = text[:4000].upper()
    if "PIPELINE-REFERENCE" in head and "MATERIALS" in head and ("END-POINT" in head or "CO-ORDS" in head):
        return "PCF"
    if re.search(r"^\s*[+-]?\d+", text, re.MULTILINE):
        return "IDF"
    return None


def upload_idf_view(request):
    if request.method == "POST":
        form = PipelineUploadForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.cleaned_data["project"]
            f1 = form.cleaned_data.get('idf_files') or []
            f2 = form.cleaned_data.get('idf_directory') or []
            all_files = f1 + f2

            grouped_payloads = {"IDF": [], "PCF": []}
            for uf in all_files:
                fname = uf.name.split('/')[-1]
                raw = uf.read()
                text = decode_pipeline_bytes(raw)
                detected_format = detect_pipeline_format(fname, text)
                if detected_format:
                    grouped_payloads[detected_format].append((fname, text))

            idf_payloads = grouped_payloads["IDF"]
            pcf_payloads = grouped_payloads["PCF"]

            if idf_payloads and pcf_payloads:
                messages.error(request, "Please upload only one source format at a time. Mixed IDF and PCF batches are not yet supported in a single scene.")
                return render(request, "idfviewer/upload.html", {"form": form})

            if not idf_payloads and not pcf_payloads:
                messages.error(request, "No valid .idf or .pcf files found in upload.")
                return render(request, "idfviewer/upload.html", {"form": form})

            if pcf_payloads:
                scene = parse_multiple_pcf_texts(pcf_payloads, project)
                filename = f"Batch: {len(pcf_payloads)} PCF file(s)"
            else:
                scene = parse_multiple_idf_texts(idf_payloads, project)
                filename = f"Batch: {len(idf_payloads)} IDF file(s)"

            return render(
                request,
                "idfviewer/viewer.html",
                {
                    "scene": scene,
                    "filename": filename,
                    "project": project
                },
            )
    else:
        form = PipelineUploadForm()

    return render(request, "idfviewer/upload.html", {"form": form})
