from rest_framework import serializers

from core.models import Feature, GeoFile

UNIT_LABEL = {"m2": "m²", "m": "m"}


class CRSSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    units = serializers.CharField(allow_null=True)


class StageSerializer(serializers.Serializer):
    stage = serializers.CharField()
    status = serializers.CharField()
    duration_ms = serializers.FloatField(allow_null=True)


class FileSummarySerializer(serializers.ModelSerializer):
    filename = serializers.CharField(source="original_filename")

    class Meta:
        model = GeoFile
        fields = ["id", "filename", "file_type", "status", "feature_count", "successful_count",
                  "failed_count", "is_sample", "created_at"]


class FileSerializer(FileSummarySerializer):
    format = serializers.CharField(source="get_file_type_display")
    crs = serializers.SerializerMethodField(help_text="Source CRS code, e.g. EPSG:4326; null when unknown")
    source_crs = CRSSerializer(allow_null=True)
    stages = StageSerializer(many=True)
    error_code = serializers.SerializerMethodField()
    error_message = serializers.SerializerMethodField()

    class Meta(FileSummarySerializer.Meta):
        fields = FileSummarySerializer.Meta.fields + [
            "format", "file_size", "crs", "source_crs", "measurement_crs", "layers", "components",
            "geometry_types", "bounds", "totals", "stages", "warnings", "processed_at", "duration_ms",
            "error_code", "error_message",
        ]

    def get_crs(self, obj) -> str | None:
        return (obj.source_crs or {}).get("code")

    def get_error_code(self, obj) -> str | None:
        return obj.error_code or None

    def get_error_message(self, obj) -> str | None:
        return obj.error_message or None


class MeasurementSerializer(serializers.Serializer):
    area_m2 = serializers.FloatField(required=False)
    area_ha = serializers.FloatField(required=False)
    length_m = serializers.FloatField(required=False)
    length_km = serializers.FloatField(required=False)
    geodesic_value = serializers.FloatField(allow_null=True, help_text="Ellipsoidal cross-check, same unit")
    method = serializers.CharField()


class FeatureMeasurementSerializer(serializers.Serializer):
    feature_id = serializers.IntegerField(help_text="1-based position in the file")
    feature_index = serializers.IntegerField(help_text="0-based position in the file")
    source_id = serializers.CharField(allow_null=True)
    layer = serializers.CharField(allow_null=True)
    geometry_type = serializers.CharField(allow_null=True)
    status = serializers.ChoiceField(choices=Feature.Status.choices)
    measurement_status = serializers.ChoiceField(choices=["measured", "not_required", "unsupported", "failed"])
    measurement_type = serializers.CharField(allow_null=True, help_text="area | length")
    value = serializers.FloatField(allow_null=True)
    unit = serializers.CharField(allow_null=True, help_text="m² | m")
    measurement = MeasurementSerializer(allow_null=True)
    source_crs = serializers.CharField(allow_null=True)
    measurement_crs = serializers.CharField(allow_null=True)
    measurement_crs_name = serializers.CharField(allow_null=True)
    properties = serializers.DictField()
    geometry = serializers.DictField(allow_null=True, help_text="GeoJSON geometry")
    geometry_crs = serializers.CharField(allow_null=True)
    error_code = serializers.CharField(allow_null=True)
    error = serializers.CharField(allow_null=True)


class MeasurementsSerializer(serializers.Serializer):
    file_id = serializers.IntegerField()
    status = serializers.CharField()
    crs = serializers.CharField(allow_null=True)
    feature_count = serializers.IntegerField()
    successful = serializers.IntegerField()
    failed = serializers.IntegerField()
    totals = serializers.DictField(allow_null=True)
    features = FeatureMeasurementSerializer(many=True)


class ErrorBodySerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField()


class ErrorSerializer(serializers.Serializer):
    error = ErrorBodySerializer()


def feature_measurement(f: Feature, include_geometry: bool = True) -> dict:
    """Same output as FeatureMeasurementSerializer, but built with plain dicts so 10,000-feature files stay fast."""
    v = f.measurement_value
    measurement = None
    if v is not None:
        measurement = ({"area_m2": round(v, 2), "area_ha": round(v / 10_000, 6)} if f.measurement_type == "area"
                       else {"length_m": round(v, 2), "length_km": round(v / 1000, 6)})
        measurement |= {"geodesic_value": f.geodesic_value, "method": "planar"}
    return {
        "feature_id": f.feature_index + 1,
        "feature_index": f.feature_index,
        "source_id": f.source_id or None,
        "layer": f.layer or None,
        "geometry_type": f.geometry_type or None,
        "status": f.status,
        "measurement_status": f.measurement_status,
        "measurement_type": f.measurement_type or None,
        "value": v,
        "unit": UNIT_LABEL.get(f.measurement_unit),
        "measurement": measurement,
        "source_crs": f.source_crs or None,
        "measurement_crs": f.measurement_crs or None,
        "measurement_crs_name": f.measurement_crs_name or None,
        "properties": f.properties or {},
        "geometry": f.geometry if include_geometry else None,
        "geometry_crs": f.geometry_crs or None,
        "error_code": f.error_code or None,
        "error": f.error_message or None,
    }
