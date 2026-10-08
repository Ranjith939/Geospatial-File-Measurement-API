"""Every API error goes out in the same shape: {"error": {"code", "message", "details"}}. We never send tracebacks."""

import logging

from django.http import Http404
from rest_framework import exceptions as drf
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler

from core.exceptions import GeoMeasureError
from core.logging import log_event


def _error(status: int, code: str, message: str, details: dict | None = None) -> Response:
    return Response({"error": {"code": code, "message": message, "details": details or {}}}, status=status)


def exception_handler(exc, context):
    if isinstance(exc, GeoMeasureError):
        log_event("request_rejected", logging.WARNING, error_type=exc.code)
        return _error(exc.status_code, exc.code, exc.message, exc.details)
    if isinstance(exc, Http404):
        return _error(404, "NOT_FOUND", "Not found.")
    if isinstance(exc, drf.ValidationError):
        return _error(422, "INVALID_REQUEST", "The request is invalid.", {"fields": exc.detail})
    if isinstance(exc, drf.UnsupportedMediaType):
        return _error(415, "UNSUPPORTED_MEDIA_TYPE", "Send the file as multipart/form-data.")
    if isinstance(exc, drf.ParseError):
        return _error(400, "INVALID_REQUEST", "The request body could not be parsed.")
    response = drf_handler(exc, context)
    if response is not None:
        return _error(response.status_code, str(exc.default_code).upper(), str(exc.detail))
    logging.getLogger("geomeasure").exception("unhandled API error")
    return _error(500, "INTERNAL_ERROR", "An unexpected error occurred.")
