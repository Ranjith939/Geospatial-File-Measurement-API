class GeoMeasureError(Exception):
    """An error we can safely show to API clients. It has a fixed code, a readable message and optional details."""

    status_code = 400

    def __init__(self, code: str, message: str, details: dict | None = None, status_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code


class ValidationFailed(GeoMeasureError):
    """We rejected the upload before saving anything."""

    status_code = 422


class ProcessingFailed(GeoMeasureError):
    """The file passed validation, but we couldn't read it at all."""

    status_code = 422


class NotFound(GeoMeasureError):
    status_code = 404
