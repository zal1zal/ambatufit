from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import User, get_db
from app.contexts.identity_access.service import require_role
from app.contexts.personal_health_intelligence.medication_catalog import (
    get_approved_medication,
    search_medications,
)
from app.contexts.personal_health_intelligence.medication_matching import (
    get_medication_info_for_assessment,
)
from app.schemas.medication import MedicationDetailDTO, MedicationInformationResponse

router = APIRouter(tags=["Personal Health Intelligence Context"])


@router.get("/medications", response_model=MedicationInformationResponse)
def list_medications(
    query: Optional[str] = Query(None, max_length=120),
    indication: Optional[str] = Query(None, max_length=120),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_role("user")),
    db: Session = Depends(get_db),
):
    return search_medications(db, query=query, indication=indication, limit=limit, offset=offset)


@router.get("/medications/{id}", response_model=MedicationDetailDTO)
def get_medication_detail(
    id: str,
    current_user: User = Depends(require_role("user")),
    db: Session = Depends(get_db),
):
    med = get_approved_medication(db, id)
    if not med:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Informasi obat terverifikasi tidak ditemukan.",
        )
    return med


@router.get(
    "/assessments/{id}/medication-information",
    response_model=MedicationInformationResponse,
)
def get_assessment_medication_information(
    id: str,
    current_user: User = Depends(require_role("user")),
    db: Session = Depends(get_db),
):
    result = get_medication_info_for_assessment(db, current_user.id, id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Penilaian kesehatan tidak ditemukan atau Anda tidak berwenang.",
        )
    return result

