from django.contrib import admin

from .models import Feature, GeoFile


@admin.register(GeoFile)
class GeoFileAdmin(admin.ModelAdmin):
    list_display = ("id", "original_filename", "file_type", "status", "feature_count", "failed_count", "created_at")
    list_filter = ("status", "file_type", "is_sample")


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ("file", "feature_index", "geometry_type", "measurement_status", "status")
    list_filter = ("status", "geometry_type")
