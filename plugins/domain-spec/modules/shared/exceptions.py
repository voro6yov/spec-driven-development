import http

__all__ = [
    "DomainException",
    "NotFound",
    "AlreadyExists",
    "Conflict",
    "Unauthorized",
    "Forbidden",
    "IllegalArgument",
    "AuthError",
]


class DomainException(Exception):
    code: str = "domain_exception"


class NotFound(DomainException):
    code: str = "not_found"


class AlreadyExists(DomainException):
    code: str = "already_exists"


class Conflict(DomainException):
    code: str = "conflict"


class Unauthorized(DomainException):
    code: str = "unauthorized"


class Forbidden(DomainException):
    code: str = "forbidden"


class IllegalArgument(DomainException):
    code: str = "illegal_argument"


class AuthError(Unauthorized):
    code: str = "authentication_error"

    def __init__(self, detail: str, status_code: int = http.HTTPStatus.UNAUTHORIZED):
        super().__init__(detail)
        self.status_code = status_code
