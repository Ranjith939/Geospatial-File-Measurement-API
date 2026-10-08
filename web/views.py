from django.shortcuts import render

from core.models import GeoFile
from .story import story_context


def landing(request):
    """The scroll story (built from real sample results) ending in the upload workspace."""
    return render(request, "web/landing.html", {"story": story_context()})


def files(request):
    return render(request, "web/files.html", {"files": GeoFile.objects.filter(is_sample=False)[:100]})


def file_detail(request, file_id: int):
    """Shell only; workspace.js loads the file and its measurements through the public API."""
    return render(request, "web/file_detail.html", {"file_id": file_id})


def api_docs(request):
    return render(request, "web/api_docs.html")
