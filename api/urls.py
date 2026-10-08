from django.urls import path

from . import views

urlpatterns = [
    path("files/", views.FileListCreateView.as_view(), name="file-list"),
    path("files/<int:file_id>/", views.FileDetailView.as_view(), name="file-detail"),
    path("files/<int:file_id>/measurements/", views.MeasurementsView.as_view(), name="file-measurements"),
    path("health/", views.HealthView.as_view(), name="health"),
]
