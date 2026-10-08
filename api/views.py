import tempfile
from pathlib import Path

from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import NotFound, ValidationFailed
from core.models import GeoFile
from processing.services.file_validator import detect_file_type, sanitize_filename
from processing.services.pipeline import process_upload

from .serializers import (
    ErrorSerializer,
    FileSerializer,
    FileSummarySerializer,
    MeasurementsSerializer,
    feature_measurement,
)

CHUNK = 1024 * 1024
ERRORS = {code: ErrorSerializer for code in (400, 413, 415, 422)}


def _too_large() -> ValidationFailed:
    return ValidationFailed("FILE_TOO_LARGE", f"Uploads are limited to {settings.MAX_UPLOAD_MB} MB.",
                            {"max_mb": settings.MAX_UPLOAD_MB}, status_code=413)


def _get_file(file_id: int) -> GeoFile:
    try:
        return GeoFile.objects.get(pk=file_id)
    except GeoFile.DoesNotExist:
        raise NotFound("FILE_NOT_FOUND", f"File {file_id} does not exist.") from None


class FileListCreateView(APIView):
    @extend_schema(
        summary="Upload a geospatial file",
        description="Upload a `.kml` file or a `.zip` containing a Shapefile. Processing is synchronous: "
                    "the response carries the final status (`completed`, `completed_with_errors` or `failed`).",
        request={"multipart/form-data": inline_serializer("Upload", {"file": serializers.FileField()})},
        responses={201: FileSerializer, **ERRORS},
    )
    def post(self, request):
        max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
        if int(request.META.get("CONTENT_LENGTH") or 0) > max_bytes + CHUNK:  # multipart overhead allowance
            raise _too_large()
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationFailed("NO_FILE", "No file was uploaded (multipart field 'file').", status_code=400)
        if upload.size > max_bytes:
            raise _too_large()
        name = sanitize_filename(upload.name)
        file_type = detect_file_type(name)
        with tempfile.TemporaryDirectory(prefix="geomeasure-upload-") as tmp:
            path = Path(tmp) / f"upload{Path(name).suffix.lower()}"
            with open(path, "wb") as out:
                for chunk in upload.chunks(CHUNK):
                    out.write(chunk)
            geo_file = process_upload(path, name, file_type)
        return Response(FileSerializer(geo_file).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="List recent uploads",
        parameters=[OpenApiParameter("limit", OpenApiTypes.INT, description="1-200, default 50")],
        responses=FileSummarySerializer(many=True),
    )
    def get(self, request):
        try:
            limit = max(1, min(int(request.query_params.get("limit", 50)), 200))
        except ValueError:
            raise ValidationFailed("INVALID_REQUEST", "limit must be an integer.") from None
        files = GeoFile.objects.filter(is_sample=False)[:limit]
        return Response(FileSummarySerializer(files, many=True).data)


class FileDetailView(APIView):
    @extend_schema(summary="Retrieve file information",
                   description="Format, status, source and measurement CRS, feature counts, layers, archive "
                               "components, WGS84 bounds, totals and per-stage timings.",
                   responses={200: FileSerializer, 404: ErrorSerializer})
    def get(self, request, file_id: int):
        return Response(FileSerializer(_get_file(file_id)).data)

    @extend_schema(summary="Delete a file and its features", responses={204: None, 404: ErrorSerializer})
    def delete(self, request, file_id: int):
        geo_file = _get_file(file_id)
        (Path(settings.MEDIA_ROOT) / "uploads" / geo_file.stored_filename).unlink(missing_ok=True)
        geo_file.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeasurementsView(APIView):
    @extend_schema(
        summary="Retrieve measurements",
        description="One entry per feature. Polygons carry area (m², ha), lines carry length (m, km), points "
                    "report `measurement_status: not_required`. Failed and unsupported features keep their "
                    "geometry and properties and carry an error code and message.",
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, enum=["success", "failed", "unsupported"]),
            OpenApiParameter("include_geometry", OpenApiTypes.BOOL, description="default true"),
        ],
        responses={200: MeasurementsSerializer, 404: ErrorSerializer, 422: ErrorSerializer},
    )
    def get(self, request, file_id: int):
        geo_file = _get_file(file_id)
        wanted = request.query_params.get("status")
        if wanted not in (None, "success", "failed", "unsupported"):
            raise ValidationFailed("INVALID_REQUEST", "status must be success, failed or unsupported.")
        include_geometry = request.query_params.get("include_geometry", "true").lower() not in ("false", "0", "no")
        features = geo_file.features.all()
        if wanted:
            features = features.filter(status=wanted)
        return Response({
            "file_id": geo_file.pk,
            "status": geo_file.status,
            "crs": (geo_file.source_crs or {}).get("code"),
            "feature_count": geo_file.feature_count,
            "successful": geo_file.successful_count,
            "failed": geo_file.failed_count,
            "totals": geo_file.totals,
            "features": [feature_measurement(f, include_geometry) for f in features],
        })


@extend_schema(exclude=True)
class HealthView(APIView):
    def get(self, request):
        return Response({"status": "ok"})

