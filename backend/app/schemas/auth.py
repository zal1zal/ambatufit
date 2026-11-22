from datetime import datetime
from typing import Optional
from pydantic import Field
from app.schemas.base import ApiModel as BaseModel


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=128)
    password: str = Field(..., min_length=6)
    display_name: Optional[str] = Field(default=None, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=128)
    password: str = Field(..., min_length=6)


class AccountUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=128)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)


class PasswordChangeResponse(BaseModel):
    status: str = "password_updated"
    message: str = "Kata sandi berhasil diperbarui. Silakan gunakan kata sandi baru untuk sesi berikutnya."


class LogoutResponse(BaseModel):
    status: str = "logged_out"
    revoked: bool = True
    message: str = "Sesi berhasil diakhiri dan token otorisasi telah dicabut di server."


class UserDTO(BaseModel):
    id: str
    email: str
    role: str
    display_name: Optional[str] = None
    created_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserDTO

