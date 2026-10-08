from django.db import models


class GeoFile(models.Model):
    class FileType(models.TextChoices):
        KML = "KML", "KML"
        SHAPEFILE = "SHAPEFILE", "ESRI Shapefile"

    class Status(models.TextChoices):
        UPLOADED = "uploaded"
        VALIDATING = "validating"
        EXTRACTING = "extracting"
        PARSING = "parsing"
        DETECTING_CRS = "detecting_crs"
        TRANSFORMING = "transforming"
        MEASURING = "measuring"
        COMPLETED = "completed"
        COMPLETED_WITH_ERRORS = "completed_with_errors"
        FAILED = "failed"

    original_filename = models.CharField(max_length=255)
    stored_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=16, choices=FileType.choices)
    file_size = models.PositiveBigIntegerField()
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.UPLOADED)

    source_crs = models.JSONField(null=True, blank=True)  # {code, name, type, units} or null
    measurement_crs = models.JSONField(default=list)  # distinct CRS codes used for measuring
    feature_count = models.PositiveIntegerField(default=0)
    successful_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)

    layers = models.JSONField(default=list)
    components = models.JSONField(default=list)  # extracted archive members: [{name, size}]
    geometry_types = models.JSONField(default=dict)
    bounds = models.JSONField(null=True, blank=True)  # WGS84 [min_lon, min_lat, max_lon, max_lat]
    totals = models.JSONField(null=True, blank=True)
    stages = models.JSONField(default=list)  # [{stage, status, duration_ms}]
    warnings = models.JSONField(default=list)
    is_sample = models.BooleanField(default=False)  # processed from sample-data/ for the landing story

    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.FloatField(null=True, blank=True)
    error_code = models.CharField(max_length=64, blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.original_filename} ({self.status})"


class Feature(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success"
        FAILED = "failed"
        UNSUPPORTED = "unsupported"

    file = models.ForeignKey(GeoFile, on_delete=models.CASCADE, related_name="features")
    feature_index = models.PositiveIntegerField()  # 0-based order within the file
    source_id = models.CharField(max_length=255, blank=True, default="")  # KML id / shapefile FID
    layer = models.CharField(max_length=255, blank=True, default="")
    geometry_type = models.CharField(max_length=32, blank=True, default="")
    # Display geometry only, as GeoJSON in WGS84 (or source coordinates when the CRS is unknown).
    # The projected copy used for measuring is derivable and would double the payload.
    geometry = models.JSONField(null=True, blank=True)
    geometry_crs = models.CharField(max_length=64, blank=True, default="")
    properties = models.JSONField(default=dict)

    source_crs = models.CharField(max_length=64, blank=True, default="")
    measurement_crs = models.CharField(max_length=64, blank=True, default="")
    measurement_crs_name = models.CharField(max_length=128, blank=True, default="")
    measurement_type = models.CharField(max_length=8, blank=True, default="")  # area | length
    measurement_value = models.FloatField(null=True, blank=True)  # m2 or m
    measurement_unit = models.CharField(max_length=4, blank=True, default="")  # m2 | m
    geodesic_value = models.FloatField(null=True, blank=True)  # ellipsoidal cross-check
    measurement_status = models.CharField(max_length=16)  # measured | not_required | unsupported | failed
    status = models.CharField(max_length=16, choices=Status.choices)
    error_code = models.CharField(max_length=64, blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["feature_index"]
        constraints = [models.UniqueConstraint(fields=["file", "feature_index"], name="unique_feature_index")]

    def __str__(self):
        return f"{self.file_id}#{self.feature_index + 1} {self.geometry_type}"
