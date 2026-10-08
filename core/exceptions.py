class GeoMeasureError(Exception):
    """An error that is safe to show to API clients: a stable code, a human message, optional details."""

    status_code = 400

    def __init__(self, code: str, message: str, details: dict | None = None, status_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code


class ValidationFailed(GeoMeasureError):
    """The upload was rejected before anything was stored."""

    status_code = 422


class ProcessingFailed(GeoMeasureError):
    """The file passed validation but could not be read as a whole."""

    status_code = 422


class NotFound(GeoMeasureError):
    status_code = 404
