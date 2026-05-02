from pydantic import BaseModel

__all__ = ["ErrorSerializer"]


class ErrorSerializer(BaseModel):
    code: str
    message: str
