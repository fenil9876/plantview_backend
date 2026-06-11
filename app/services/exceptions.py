"""Framework-light service errors, mapped to HTTP responses in main.py."""


class ServiceError(Exception):
    status_code: int = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class NotFound(ServiceError):
    status_code = 404


class Forbidden(ServiceError):
    status_code = 403


class Conflict(ServiceError):
    status_code = 409


class BadRequest(ServiceError):
    status_code = 400


class DataValidationError(ServiceError):
    """Payload failed validation against the stage's field definitions."""
    status_code = 422

    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init__({"message": "Validation failed", "errors": errors})
