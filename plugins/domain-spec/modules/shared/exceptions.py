import http

__all__ = [
    "ProfilesException",
    "NotFound",
    "AlreadyExists",
    "Conflict",
    "Unauthorized",
    "Forbidden",
    "IllegalArgument",
    "AuthError",
]


class ProfilesException(Exception):
    code: str = "domain_exception"


class NotFound(ProfilesException):
    code: str = "not_found"


class AlreadyExists(ProfilesException):
    code: str = "already_exists"


class Conflict(ProfilesException):
    code: str = "conflict"


class Unauthorized(ProfilesException):
    code: str = "unauthorized"


class Forbidden(ProfilesException):
    code: str = "forbidden"


class IllegalArgument(ProfilesException):
    code: str = "illegal_argument"


class AuthError(Unauthorized):
    code: str = "authentication_error"

    def __init__(self, detail: str, status_code: int = http.HTTPStatus.UNAUTHORIZED):
        super().__init__(detail)
        self.status_code = status_code
