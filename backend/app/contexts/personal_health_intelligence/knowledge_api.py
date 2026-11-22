"""Unified Disease Search, Medication Product Search & Knowledge Registry endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.clients.ai_client import ai_client
from app.contexts.identity_access.service import get_current_user
from app.db import User
from app.schemas.rag_plan import (
    DiseaseDetailDTO,
    DiseaseSearchResponse,
    DiseaseSummaryDTO,
    MedicationProductDTO,
    MedicationProductSearchResponse,
)

router = APIRouter(tags=["Knowledge & Search Context"])


@router.get("/diseases", response_model=DiseaseSearchResponse)
async def search_diseases(
    query: str = Query("", max_length=160),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
):
    res = await ai_client.search_diseases(query=query, limit=limit, offset=offset)
    qi = res.get("query_info") or {}
    corrected = (
        qi.get("corrected")
        if qi.get("typo_corrections") and qi.get("corrected") != qi.get("normalized")
        else None
    )
    items = [DiseaseSummaryDTO(**it) for it in res.get("items") or []]
    return DiseaseSearchResponse(
        items=items,
        total=int(res.get("total", len(items))),
        ambiguous=bool(res.get("ambiguous", False)),
        suggestions=list(res.get("suggestions") or []),
        corrected_query=corrected,
    )


@router.get("/diseases/{id}", response_model=DiseaseDetailDTO)
async def get_disease_detail(
    id: str,
    _user: User = Depends(get_current_user),
):
    item = await ai_client.get_disease(id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Informasi penyakit tidak ditemukan dalam katalog.",
        )
    return DiseaseDetailDTO(**item)


@router.get("/knowledge/medications", response_model=MedicationProductSearchResponse)
async def search_medication_knowledge(
    query: str = Query("", max_length=160),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
):
    res = await ai_client.search_knowledge_medications(query=query, limit=limit, offset=offset)
    qi = res.get("query_info") or {}
    corrected = (
        qi.get("corrected")
        if qi.get("typo_corrections") and qi.get("corrected") != qi.get("normalized")
        else None
    )
    items = [MedicationProductDTO(**it) for it in res.get("items") or []]
    return MedicationProductSearchResponse(
        items=items,
        total=int(res.get("total", len(items))),
        corrected_query=corrected,
    )


@router.get("/knowledge/medications/{id}", response_model=MedicationProductDTO)
async def get_medication_knowledge_detail(
    id: str,
    _user: User = Depends(get_current_user),
):
    item = await ai_client.get_knowledge_medication(id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produk obat tidak ditemukan dalam indeks pengetahuan.",
        )
    return MedicationProductDTO(**item)


@router.get("/knowledge/sources")
async def get_knowledge_sources(_user: User = Depends(get_current_user)):
    return await ai_client.get_rag_stats()

