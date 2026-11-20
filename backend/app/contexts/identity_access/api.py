from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.db import get_db, User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserDTO
from app.schemas.consultation import ConsentRequest, ConsentResponse
from app.contexts.identity_access.service import (
    IdentityService,
    get_current_user,
)

router = APIRouter(tags=["Identity & Access Context"])


@router.post("/auth/register", response_model=UserDTO, status_code=status.HTTP_201_CREATED)
def register_user(
    req: RegisterRequest,
    db: Session = Depends(get_db),
):
    service = IdentityService(db)
    return service.register(req)


@router.post("/auth/login", response_model=TokenResponse)
def login_user(
    req: LoginRequest,
    db: Session = Depends(get_db),
):
    service = IdentityService(db)
    return service.login(req)


@router.get("/auth/me", response_model=UserDTO)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    return UserDTO(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        created_at=current_user.created_at,
    )


@router.post("/consents/assessment-sharing", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
def grant_sharing_consent(
    req: ConsentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = IdentityService(db)
    return service.create_consent(current_user.id, req)


@router.delete("/consents/assessment-sharing/{id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_sharing_consent(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = IdentityService(db)
    success = service.revoke_consent(current_user.id, id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persetujuan tidak ditemukan atau sudah dicabut.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

