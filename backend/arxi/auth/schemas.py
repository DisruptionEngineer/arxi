from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    full_name: str
    role: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
