from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.orm import Session

from app.db import get_db, User, Assessment, Booking
from app.config import settings
from app.security import verify_password, create_access_token, decode_access_token
from app.contexts.identity_access.repository import IdentityRepository
from app.schemas.auth import UserDTO, TokenResponse, RegisterRequest, LoginRequest
from app.schemas.consultation import ConsentRequest, ConsentResponse

security_bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentikasi diperlukan. Sertakan token bearer pada header Authorization.",
        )
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token otorisasi tidak valid atau telah kedaluwarsa.",
        )
    user_id = payload.get("sub")
    repo = IdentityRepository(db)
    user = repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pengguna tidak ditemukan.",
        )
    return user


def require_role(required_role: str):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Akses ditolak. Peran '{required_role}' diperlukan.",
            )
        return current_user
    return role_checker


def verify_partner_api_key(
    api_key: Optional[str] = Security(api_key_header),
) -> str:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header X-API-Key diperlukan untuk akses layanan partner.",
        )
    partner_map = settings.partner_key_dict
    if api_key not in partner_map:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key partner tidak valid atau tidak memiliki akses.",
        )
    return partner_map[api_key]  # returns provider_id e.g. "ambatunoutrish" or "ambatomove"


class IdentityService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = IdentityRepository(db)

    def register(self, req: RegisterRequest, role: str = "user") -> UserDTO:
        existing = self.repo.get_user_by_email(req.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email sudah terdaftar dalam sistem.",
            )
        user = self.repo.create_user(email=req.email, password=req.password, role=role)
        return UserDTO(id=user.id, email=user.email, role=user.role, created_at=user.created_at)

    def login(self, req: LoginRequest) -> TokenResponse:
        user = self.repo.get_user_by_email(req.email)
        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email atau kata sandi tidak sesuai.",
            )
        token = create_access_token(user_id=user.id, role=user.role, email=user.email)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.JWT_TTL_MINUTES * 60,
            user=UserDTO(id=user.id, email=user.email, role=user.role, created_at=user.created_at),
        )

    def create_consent(self, user_id: str, req: ConsentRequest) -> ConsentResponse:
        assessment = self.db.get(Assessment, req.assessment_id)
        booking = self.db.get(Booking, req.booking_id)
        if (not assessment or assessment.user_id != user_id or not booking
                or booking.user_id != user_id or booking.professional_id != req.professional_id):
            raise HTTPException(status_code=403, detail='Izin harus sesuai penilaian, pemesanan, dan profesional milik Anda.')
        expiry = req.expires_at or (datetime.now(timezone.utc) + timedelta(days=7))
        if expiry <= datetime.now(timezone.utc):
            raise HTTPException(status_code=422, detail='Masa berlaku izin harus di waktu mendatang.')
        # Replacing scope must not leave a second active grant behind after revocation.
        from app.db import AssessmentShareConsent
        self.db.query(AssessmentShareConsent).filter(
            AssessmentShareConsent.booking_id == req.booking_id,
            AssessmentShareConsent.user_id == user_id,
            AssessmentShareConsent.is_active == True,
        ).update({'is_active': False, 'revoked_at': datetime.utcnow()})
        consent = self.repo.create_consent(
            user_id=user_id,
            assessment_id=req.assessment_id,
            professional_id=req.professional_id,
            booking_id=req.booking_id,
            expires_at=expiry.astimezone(timezone.utc).replace(tzinfo=None),
        )
        return ConsentResponse(id=consent.id, status="active" if consent.is_active else "revoked")

    def revoke_consent(self, user_id: str, consent_id: str) -> bool:
        return self.repo.revoke_consent(user_id, consent_id)

