from django.urls import path

from . import views

app_name = "web"
urlpatterns = [
    path("", views.landing, name="landing"),
    path("files/", views.files, name="files"),
    path("files/<int:file_id>/", views.file_detail, name="file_detail"),
    path("api-docs/", views.api_docs, name="api_docs"),
]
