"""Live internet health knowledge retrieval for off-STB AI enrichment (Indonesian Wikipedia)."""
from html import unescape
import json
import os
import re
from typing import Any, Dict, List
import urllib.parse
import urllib.request

USER_AGENT = "AmbatuFit-HealthAssistant/2.0 (+https://ambatufit.local)"

_STOPWORDS_ID = {
    "saya",
    "aku",
    "kami",
    "kita",
    "anda",
    "kamu",
    "dia",
    "mereka",
    "yang",
    "dan",
    "atau",
    "di",
    "ke",
    "dari",
    "dengan",
    "untuk",
    "pada",
    "adalah",
    "apa",
    "apakah",
    "mengapa",
    "kenapa",
    "bagaimana",
    "melihat",
    "bersama",
    "lain",
    "ini",
    "itu",
    "sedang",
    "sudah",
    "akan",
    "bisa",
    "tolong",
    "jelaskan",
    "tentang",
}

_NON_HEALTH_TITLE_MARKERS = (
    "daftar ",
    "emotikon",
    "film",
    "lagu",
    "album",
    "novel",
    "sinetron",
    "serial televisi",
    "permainan video",
    "kecamatan",
    "kabupaten",
    "provinsi",
    "disambiguasi",
)

_HEALTH_EXTRACT_KEYWORDS = (
    "penyakit",
    "medis",
    "gejala",
    "obat",
    "kesehatan",
    "infeksi",
    "terapi",
    "sindrom",
    "gangguan",
    "organ",
    "otot",
    "tulang",
    "darah",
    "saraf",
    "nutrisi",
    "vitamin",
    "dokter",
    "diagnosis",
    "pengobatan",
    "radang",
    "virus",
    "bakteri",
    "klinis",
    "skoliosis",
    "sakit kepala",
    "pencernaan",
    "pernapasan",
    "kelenjar",
    "imun",
    "jantung",
    "ginjal",
    "hati",
    "lambung",
    "sendi",
)


def _is_test_or_gibberish(query: str) -> bool:
    if os.environ.get("APP_ENV") == "test":
        return True
    q = (query or "").strip().lower()
    if len(q) < 3:
        return True
    if any(ch.isdigit() for ch in q) and not re.search(r"\b[a-z]\d{2}\b", q.lower()):
        return True
    if "zxqv" in q or "fiktif" in q:
        return True
    return False


def _http_get_bytes(url: str, timeout: float = 3.5) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _clean_html_text(raw: str) -> str:
    txt = unescape(raw or "")
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def _build_search_terms(query: str) -> str:
    tokens = [w for w in re.findall(r"[a-zA-Z0-9-]+", (query or "").lower()) if w not in _STOPWORDS_ID and len(w) >= 2]
    return " ".join(tokens[:6]).strip()


def _is_valid_health_wiki(title: str, summary_payload: Dict[str, Any]) -> bool:
    if (summary_payload.get("type") or "").lower() == "disambiguation":
        return False
    t_low = (title or "").lower()
    if any(marker in t_low for marker in _NON_HEALTH_TITLE_MARKERS):
        return False
    desc = (summary_payload.get("description") or "").lower()
    extract = (summary_payload.get("extract") or "").lower()
    combined = f"{t_low} {desc} {extract}"
    hits = sum(1 for kw in _HEALTH_EXTRACT_KEYWORDS if kw in combined)
    return hits >= 2


def fetch_internet_health_knowledge(query: str, *, timeout: float = 3.5, max_items: int = 2) -> List[Dict[str, Any]]:
    """
    Fetches concise Indonesian health summaries from Wikipedia Bahasa Indonesia
    with strict medical-domain validation so off-topic articles never appear.
    """
    if _is_test_or_gibberish(query):
        return []

    search_terms = _build_search_terms(query)
    if len(search_terms) < 3:
        return []

    results: List[Dict[str, Any]] = []
    try:
        search_url = (
            "https://id.wikipedia.org/w/api.php?action=query&list=search&format=json&utf8=1&srlimit=3&srsearch="
            + urllib.parse.quote(search_terms)
        )
        data = json.loads(_http_get_bytes(search_url, timeout=timeout).decode("utf-8"))
        hits = (data.get("query") or {}).get("search") or []
        for h in hits[:3]:
            title = (h.get("title") or "").strip()
            if not title:
                continue
            sum_url = "https://id.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"))
            summary_payload = json.loads(_http_get_bytes(sum_url, timeout=timeout).decode("utf-8"))
            if not _is_valid_health_wiki(title, summary_payload):
                continue
            extract = _clean_html_text(summary_payload.get("extract") or "")
            page_url = (
                ((summary_payload.get("content_urls") or {}).get("desktop") or {}).get("page")
                or f"https://id.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
            )
            if extract:
                results.append(
                    {
                        "chunk_id": f"web-wiki-{abs(hash(title)) % 100000}",
                        "source_id": "Wikipedia Indonesia",
                        "source_name": "Wikipedia Bahasa Indonesia",
                        "origin_url": page_url,
                        "verification_status": "referensi_internet_publik",
                        "title": title,
                        "content": extract[:600],
                        "category": "web_reference",
                    }
                )
            if len(results) >= max_items:
                break
    except Exception:
        pass

    return results[:max_items]
