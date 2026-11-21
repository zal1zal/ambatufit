"""Personalized Health Plan & Unified Progress Tracking API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.contexts.identity_access.service import get_current_user
from app.contexts.personal_health_intelligence.plan_service import PlanService
from app.db import User, get_db
from app.schemas.common import PaginatedResponse
from app.schemas.rag_plan import (
    PersonalizedPlanDTO,
    PlanDraftRequest,
    PlanReviseRequest,
    ProgressSummaryResponse,
)

router = APIRouter(tags=["Personalized Health Plan & Progress Context"])


@router.post("/plans/draft", response_model=PersonalizedPlanDTO, status_code=status.HTTP_201_CREATED)
async def create_plan_draft(
    body: PlanDraftRequest = PlanDraftRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await PlanService(db).create_draft(current_user.id, body)


@router.get("/plans", response_model=PaginatedResponse[PersonalizedPlanDTO])
def list_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = PlanService(db).list_plans(current_user.id)
    return PaginatedResponse(items=items, total=len(items))


@router.get("/plans/{id}", response_model=PersonalizedPlanDTO)
def get_plan(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = PlanService(db).get_plan(current_user.id, id)
    if not plan:
        raise HTTPException(status_code=404, detail="Rencana personal tidak ditemukan.")
    return plan


@router.post("/plans/{id}/activate", response_model=PersonalizedPlanDTO)
def activate_plan(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        plan = PlanService(db).activate_plan(current_user.id, id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not plan:
        raise HTTPException(status_code=404, detail="Rencana personal tidak ditemukan.")
    return plan


@router.post("/plans/{id}/revise", response_model=PersonalizedPlanDTO, status_code=status.HTTP_201_CREATED)
async def revise_plan(
    id: str,
    body: PlanReviseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = await PlanService(db).revise_plan(current_user.id, id, body)
    if not plan:
        raise HTTPException(status_code=404, detail="Rencana personal tidak ditemukan.")
    return plan


@router.get("/progress/summary", response_model=ProgressSummaryResponse)
def get_progress_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return PlanService(db).get_progress_summary(current_user.id)

