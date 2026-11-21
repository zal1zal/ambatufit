from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db, User
from app.contexts.personal_health_intelligence.service import HealthService
from app.contexts.personal_health_intelligence.evidence_catalog import get_catalog_items
from app.schemas.health import (
    HealthProfileDTO,
    AssessmentRequest,
    AssessmentResponse,
    AssessmentListItem,
    EvidenceCatalogItem,
    GuidanceResponse,
    MonitoringEntryRequest,
    MonitoringEntryResponse,
    CapabilityResponse,
)
from app.schemas.common import PaginatedResponse
from app.contexts.identity_access.service import get_current_user

router = APIRouter(tags=["Personal Health Intelligence Context"])


@router.get("/profile", response_model=HealthProfileDTO)
def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HealthService(db)
    return service.get_profile(current_user.id)


@router.put("/profile", response_model=HealthProfileDTO)
def update_user_profile(
    profile_in: HealthProfileDTO,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HealthService(db)
    return service.update_profile(current_user.id, profile_in)


@router.get("/assessments/evidences", response_model=PaginatedResponse[EvidenceCatalogItem])
def get_evidence_catalog():
    items = get_catalog_items()
    return PaginatedResponse(items=items, total=len(items))


@router.post("/assessments", response_model=AssessmentResponse)
async def create_assessment(
    req: AssessmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HealthService(db)
    try:
        return await service.perform_assessment(current_user.id, req)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.get("/assessments", response_model=PaginatedResponse[AssessmentListItem])
def list_assessments(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HealthService(db)
    items, total = service.list_assessments(current_user.id, limit, offset)
    return PaginatedResponse(
        items=[AssessmentListItem(**item) for item in items],
        total=total,
    )


@router.get("/assessments/{id}", response_model=AssessmentResponse)
def get_assessment_detail(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HealthService(db)
    res = service.get_assessment(current_user.id, id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Penilaian kesehatan tidak ditemukan atau Anda tidak berwenang.",
        )
    return res


@router.get("/guidance", response_model=GuidanceResponse)
async def get_guidance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HealthService(db)
    return await service.get_personalized_guidance(current_user.id)


@router.post("/monitoring/entries", response_model=MonitoringEntryResponse)
def add_monitoring_entry(
    req: MonitoringEntryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HealthService(db)
    return service.add_monitoring_entry(current_user.id, req)


@router.get("/monitoring/entries", response_model=PaginatedResponse[MonitoringEntryResponse])
def list_monitoring_entries(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HealthService(db)
    items, total = service.list_monitoring_entries(current_user.id, limit, offset)
    return PaginatedResponse(items=items, total=total)


@router.get("/system/capabilities", response_model=CapabilityResponse)
async def get_capabilities(
    db: Session = Depends(get_db),
):
    service = HealthService(db)
    return await service.get_system_capabilities()

