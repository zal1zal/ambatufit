from typing import List, Dict, Any, Optional
from app.schemas.health import EvidenceCatalogItem, EvidenceCatalogOption

# Synthetic questionnaire codes for coursework only, NOT verified DDXPlus IDs.
# Replace with actual reviewed release metadata before enabling model-backed use.
CATALOG_ITEMS: List[EvidenceCatalogItem] = [
    EvidenceCatalogItem(
        evidence_code="E_SEVERE_CHEST_PAIN",
        label_id="Nyeri Dada Hebat",
        question_id="Apakah Anda merasakan nyeri atau sensasi tertekan yang kuat di dada?",
        value_type="boolean",
    ),
    EvidenceCatalogItem(
        evidence_code="E_SHORTNESS_OF_BREATH",
        label_id="Sesak Napas",
        question_id="Apakah Anda mengalami kesulitan bernapas atau sesak napas saat istirahat?",
        value_type="boolean",
    ),
    EvidenceCatalogItem(
        evidence_code="E_SUDDEN_NUMBNESS",
        label_id="Mati Rasa Mendadak",
        question_id="Apakah ada anggota tubuh (wajah, lengan, kaki) yang terasa lemas atau mati rasa tiba-tiba?",
        value_type="boolean",
    ),
    EvidenceCatalogItem(
        evidence_code="E_SLURRED_SPEECH",
        label_id="Bicara Cadal / Pelo",
        question_id="Apakah Anda atau orang lain menyadari kesulitan berbicara atau ucapan tidak jelas?",
        value_type="boolean",
    ),
    EvidenceCatalogItem(
        evidence_code="E_HIGH_FEVER",
        label_id="Demam Tinggi",
        question_id="Apakah suhu tubuh Anda terukur sangat tinggi (di atas 39°C) atau terasa sangat panas?",
        value_type="boolean",
    ),
    EvidenceCatalogItem(
        evidence_code="E_STIFF_NECK",
        label_id="Kaku Kuduk",
        question_id="Apakah leher terasa kaku dan sulit/sakit saat dagu ditekuk ke arah dada?",
        value_type="boolean",
    ),
    EvidenceCatalogItem(
        evidence_code="E_SEVERE_ALLERGIC_REACTION",
        label_id="Reaksi Alergi Berat",
        question_id="Apakah muncul bentol-bentol kemerahan luas dan rasa terbakar pada kulit?",
        value_type="boolean",
    ),
    EvidenceCatalogItem(
        evidence_code="E_THROAT_TIGHTNESS",
        label_id="Tenggorokan Menyempit",
        question_id="Apakah tenggorokan terasa tersumbat atau sulit menelan ludah/bernapas?",
        value_type="boolean",
    ),
    EvidenceCatalogItem(
        evidence_code="E_PERSISTENT_FEVER_OVER_3_DAYS",
        label_id="Demam Lebih Dari 3 Hari",
        question_id="Apakah demam sudah berlangsung terus-menerus selama lebih dari 3 hari?",
        value_type="boolean",
    ),
    EvidenceCatalogItem(
        evidence_code="E_COUGH",
        label_id="Batuk",
        question_id="Apakah Anda mengalami batuk?",
        value_type="categorical",
        options=[
            EvidenceCatalogOption(value="dry", label_id="Batuk Kering"),
            EvidenceCatalogOption(value="productive", label_id="Batuk Berdahak"),
            EvidenceCatalogOption(value="none", label_id="Tidak Batuk"),
        ],
    ),
    EvidenceCatalogItem(
        evidence_code="E_JOINT_OR_MUSCLE_PAIN",
        label_id="Nyeri Sendi atau Otot",
        question_id="Apakah Anda merasakan nyeri pada persendian atau otot (misal setelah berolahraga)?",
        value_type="boolean",
    ),
    EvidenceCatalogItem(
        evidence_code="E_FATIGUE",
        label_id="Kelelahan / Rasa Lemah",
        question_id="Apakah Anda merasa sangat lelah dan tidak bertenaga sepanjang hari?",
        value_type="boolean",
    ),
    EvidenceCatalogItem(
        evidence_code="E_HEADACHE",
        label_id="Sakit Kepala",
        question_id="Apakah Anda merasakan sakit kepala berdenyut atau tegang?",
        value_type="categorical",
        options=[
            EvidenceCatalogOption(value="mild", label_id="Ringan"),
            EvidenceCatalogOption(value="moderate", label_id="Sedang"),
            EvidenceCatalogOption(value="severe", label_id="Berat"),
            EvidenceCatalogOption(value="none", label_id="Tidak Sakit"),
        ],
    ),
    EvidenceCatalogItem(
        evidence_code="E_NAUSEA",
        label_id="Mual / Gangguan Pencernaan",
        question_id="Apakah Anda merasa mual atau perut terasa tidak nyaman?",
        value_type="boolean",
    ),
]


def get_catalog_items() -> List[EvidenceCatalogItem]:
    from app.config import settings
    if settings.APP_ENV not in ('development', 'test'):
        return []
    return CATALOG_ITEMS


def get_catalog_dict() -> Dict[str, EvidenceCatalogItem]:
    return {item.evidence_code: item for item in get_catalog_items()}

