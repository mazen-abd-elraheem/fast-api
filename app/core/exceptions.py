"""
Sanaie Platform — Custom Domain Exceptions
Services raise these instead of HTTPException, keeping them HTTP-agnostic.
The API layer catches these and converts to proper HTTP responses.
"""


class SanaieException(Exception):
    """Base exception for all Sanaie platform errors."""
    def __init__(self, message: str = "An error occurred"):
        self.message = message
        super().__init__(self.message)


class NotFoundException(SanaieException):
    """Resource not found (→ HTTP 404)."""
    def __init__(self, resource: str = "Resource", identifier: str = ""):
        msg = f"{resource} not found" + (f": {identifier}" if identifier else "")
        super().__init__(msg)


class DuplicateException(SanaieException):
    """Resource already exists (→ HTTP 409)."""
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message)


class ForbiddenException(SanaieException):
    """User lacks permission (→ HTTP 403)."""
    def __init__(self, message: str = "You do not have permission"):
        super().__init__(message)


class BadRequestException(SanaieException):
    """Invalid operation or data (→ HTTP 400)."""
    def __init__(self, message: str = "Bad request"):
        super().__init__(message)


class UnauthorizedException(SanaieException):
    """Authentication failed (→ HTTP 401)."""
    def __init__(self, message: str = "Not authenticated"):
        super().__init__(message)
