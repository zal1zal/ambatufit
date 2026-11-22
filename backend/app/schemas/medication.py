from datetime import datetime
from typing import List, Literal
from pydantic import Field
from app.schemas.base import ApiModel as BaseModel

MEDICATION_DISCLAIMER = (
    "Informasi obat ini bersifat edukatif dan bukan resep atau rekomendasi pengobatan individual."
)
MEDICATION_RESTRICTED_MESSAGE = (
    "Informasi opsi obat untuk keluhan ini dibatasi. Silakan berkonsultasi dengan dokter atau apoteker."
)
MEDICATION_UNAVAILABLE_MESSAGE = (
    "Informasi obat terverifikasi belum tersedia untuk keluhan atau pencarian ini."
)
PRESCRIPTION_EDUCATION_NOTICE = (
    "Obat yang memerlukan resep dokter tidak direkomendasikan untuk penggunaan mandiri. "
    "Konsultasikan dengan dokter atau apoteker."
)

MedicationCategory = Literal["obat_bebas", "obat_bebas_terbatas"]
MedicationInfoStatus = Literal["available", "restricted", "unavailable"]


class MedicationSourceDTO(BaseModel):
    reference_id: str
    title: str
    url: str
    verified_at: datetime


class MedicationDetailDTO(BaseModel):
    id: str
    display_name: str
    active_ingredient: str
    category: MedicationCategory
    general_indications: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    contraindications: List[str] = Field(default_factory=list)
    source: MedicationSourceDTO
    disclaimer: str = MEDICATION_DISCLAIMER


class MedicationInformationResponse(BaseModel):
    items: List[MedicationDetailDTO] = Field(default_factory=list)
    total: int = 0
    information_status: MedicationInfoStatus
    message: str = ""

