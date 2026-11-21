import difflib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from sqlalchemy.orm import Session

from app.config import RULES_DIR
from app.db import MedicationCatalogItem
from app.schemas.medication import (
    MEDICATION_DISCLAIMER,
    MEDICATION_UNAVAILABLE_MESSAGE,
    MedicationDetailDTO,
    MedicationInformationResponse,
    MedicationSourceDTO,
)

CATALOG_FILE = RULES_DIR / "medication_catalog.reviewed.json"
ALLOWED_CATEGORIES = frozenset({"obat_bebas", "obat_bebas_terbatas"})


def parse_utc(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    if isinstance(value, str) and value.strip() and "<" not in value:
        try:
            dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def _is_valid_https_url(url: Any) -> bool:
    if not isinstance(url, str) or "<" in url or ">" in url:
        return False
    parsed = urlparse(url.strip())
    return parsed.scheme == "https" and bool(parsed.netloc)


def _str_list(raw: Any) -> List[str]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    return [str(v).strip() for v in raw if str(v).strip()] if isinstance(raw, list) else []


def is_approved_catalog_record(rec: Dict[str, Any], now: datetime) -> bool:
    if rec.get("review_status") != "reviewed":
        return False
    if rec.get("category") not in ALLOWED_CATEGORIES:
        return False
    required = ("id", "display_name", "active_ingredient", "source_reference_id", "source_title")
    if not all(isinstance(rec.get(k), str) and rec[k].strip() for k in required):
        return False
    if not _is_valid_https_url(rec.get("source_url")):
        return False
    if parse_utc(rec.get("verified_at")) is None:
        return False
    if rec.get("expires_at") is not None:
        exp = parse_utc(rec.get("expires_at"))
        if exp is None or exp <= now:
            return False
    return True


def _row_to_record(row: MedicationCatalogItem) -> Dict[str, Any]:
    return {
        "id": row.id,
        "display_name": row.display_name,
        "active_ingredient": row.active_ingredient,
        "category": row.category,
        "general_indications": _str_list(row.general_indications_json),
        "warnings": _str_list(row.warnings_json),
        "contraindications": _str_list(row.contraindications_json),
        "source_reference_id": row.source_reference_id,
        "source_title": row.source_title,
        "source_url": row.source_url,
        "verified_at": row.verified_at,
        "expires_at": row.expires_at,
        "review_status": row.review_status,
        "review_version": row.review_version,
    }


def _to_dto(rec: Dict[str, Any]) -> MedicationDetailDTO:
    verified_at = parse_utc(rec["verified_at"])
    return MedicationDetailDTO(
        id=rec["id"].strip(),
        display_name=rec["display_name"].strip(),
        active_ingredient=rec["active_ingredient"].strip(),
        category=rec["category"],
        general_indications=_str_list(rec.get("general_indications")),
        warnings=_str_list(rec.get("warnings")),
        contraindications=_str_list(rec.get("contraindications")),
        source=MedicationSourceDTO(
            reference_id=rec["source_reference_id"].strip(),
            title=rec["source_title"].strip(),
            url=rec["source_url"].strip(),
            verified_at=verified_at,
        ),
        disclaimer=MEDICATION_DISCLAIMER,
    )


def _load_raw_catalog(db: Optional[Session], rules_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    if rules_path is None and db is not None:
        rows = db.query(MedicationCatalogItem).all()
        if rows:
            return [_row_to_record(r) for r in rows]

    path = rules_path or CATALOG_FILE
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = payload.get("items", []) if isinstance(payload, dict) else payload
    return items if isinstance(items, list) else []


def list_approved_medications(
    db: Optional[Session],
    *,
    now: Optional[datetime] = None,
    rules_path: Optional[Path] = None,
) -> List[MedicationDetailDTO]:
    ref_now = parse_utc(now) or datetime.now(timezone.utc)
    return [
        _to_dto(rec)
        for rec in _load_raw_catalog(db, rules_path=rules_path)
        if isinstance(rec, dict) and is_approved_catalog_record(rec, ref_now)
    ]


def get_approved_medication(
    db: Optional[Session],
    medication_id: str,
    *,
    now: Optional[datetime] = None,
    rules_path: Optional[Path] = None,
) -> Optional[MedicationDetailDTO]:
    for item in list_approved_medications(db, now=now, rules_path=rules_path):
        if item.id == medication_id:
            return item
    return None


def _is_subsequence(q: str, token: str) -> bool:
    if len(q) < 4 or not q.isalpha() or len(token) < len(q) or q[0] != token[0]:
        return False
    it = iter(token)
    return all(ch in it for ch in q)


def search_medications(
    db: Optional[Session],
    *,
    query: Optional[str] = None,
    indication: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    now: Optional[datetime] = None,
    rules_path: Optional[Path] = None,
) -> MedicationInformationResponse:
    approved = list_approved_medications(db, now=now, rules_path=rules_path)
    if not approved:
        return MedicationInformationResponse(
            items=[],
            total=0,
            information_status="unavailable",
            message=MEDICATION_UNAVAILABLE_MESSAGE,
        )

    q = (query or "").strip().lower()
    ind = (indication or "").strip().lower()
    syn_map = {
        "parasetamol": "paracetamol",
        "acetaminophen": "paracetamol",
        "asetaminofen": "paracetamol",
        "setirizin": "cetirizine",
        "loratadin": "loratadine",
        "omeprazol": "omeprazole",
        "famotidin": "famotidine",
        "loperamid": "loperamide",
        "ambroksol": "ambroxol",
        "bromheksin": "bromhexine",
        "asetilsistein": "acetylcysteine",
        "ctm": "chlorpheniramine",
        "klorfeniramin": "chlorpheniramine",
        "simetikon": "simethicone",
        "bisakodil": "bisacodyl",
        "laktulosa": "lactulose",
        "asam folat": "folic acid",
        "zat besi": "ferrous",
        "tambah darah": "ferrous",
        "setraline": "sertraline",
        "strln": "sertraline",
    }
    q_variants = [q, syn_map.get(q, q)] if q else []

    def _matches_q(item: MedicationDetailDTO) -> bool:
        if not q:
            return True
        hay = [
            item.display_name.lower(),
            item.active_ingredient.lower(),
            *(g.lower() for g in item.general_indications),
        ]
        for qv in q_variants:
            if any(qv in h for h in hay):
                return True
        if len(q) >= 4:
            tokens = [tok for h in hay for tok in h.split() if len(tok) >= 4]
            if difflib.get_close_matches(q, tokens, n=1, cutoff=0.72):
                return True
            if any(_is_subsequence(q, tok) for tok in tokens):
                return True
        return False

    filtered = [
        item
        for item in approved
        if _matches_q(item)
        and (not ind or any(ind in g.lower() for g in item.general_indications))
    ]
    page = filtered[offset : offset + limit]
    msg = (
        MEDICATION_DISCLAIMER
        if page
        else "Tidak ada informasi obat bebas atau obat bebas terbatas yang cocok dengan pencarian Anda."
    )
    return MedicationInformationResponse(
        items=page,
        total=len(filtered),
        information_status="available",
        message=msg,
    )

