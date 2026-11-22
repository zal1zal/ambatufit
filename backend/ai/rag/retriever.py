"""
Hybrid Query Understanding, Disease Search, Medication Product Search, and Evidence Retrieval.
Combines exact alias/code lookup, conservative typo correction, FTS5 BM25 lexical search,
semantic vector similarity, metadata filtering, and RRF fusion.
"""
import difflib
from functools import lru_cache
import re
from typing import Any, Dict, List, Optional, Tuple

from ai.rag.embeddings import RAGVectorIndex
from ai.rag.store import RAGStore

MIN_EVIDENCE_SCORE = 0.38
MIN_ENTITY_SCORE = 0.36

QUERY_STOPWORDS = frozenset(
    {
        "apa", "itu", "yang", "dan", "atau", "untuk", "dengan", "hari", "ini",
        "saat", "jika", "bila", "cara", "bagaimana", "kenapa", "mengapa",
        "lebih", "saja", "saya", "anda", "dari", "pada", "dalam", "bisa",
        "tentang", "seputar", "mohon", "tolong", "jelaskan", "penyakit",
        "obat", "gejala", "info", "informasi", "sakit", "terapi",
        "the", "and", "for", "with", "what", "how", "why", "are", "you", "your",
    }
)

BILINGUAL_SYNONYMS: Dict[str, List[str]] = {
    "darah tinggi": ["hipertensi", "hypertension", "high blood pressure", "I10"],
    "hipertensi": ["hypertension", "high blood pressure", "darah tinggi", "I10"],
    "hypertension": ["hipertensi", "high blood pressure", "darah tinggi", "I10"],
    "tensi tinggi": ["hipertensi", "hypertension", "high blood pressure"],
    "kencing manis": ["diabetes", "diabetes mellitus", "E11", "E10"],
    "diabetes": ["diabetes mellitus", "kencing manis", "gula darah tinggi", "E11"],
    "dm": ["diabetes mellitus", "diabetes", "E11"],
    "gula darah": ["diabetes mellitus", "diabetes"],
    "maag": ["gerd", "gastritis", "gastroesophageal reflux disease", "acid reflux"],
    "asam lambung": ["gerd", "gastroesophageal reflux disease", "acid reflux", "heartburn", "omeprazole"],
    "gerd": ["gastroesophageal reflux disease", "asam lambung", "heartburn", "K21"],
    "tbc": ["tuberculosis", "tuberkulosis", "A15"],
    "tb": ["tuberculosis", "tuberkulosis"],
    "ispa": ["urti", "common cold", "upper respiratory tract infection", "pilek"],
    "ppok": ["copd", "chronic obstructive pulmonary disease"],
    "radang paru": ["pneumonia", "J18"],
    "paru basah": ["pneumonia"],
    "bengek": ["asthma", "asma", "bronchospasm"],
    "asma": ["asthma", "bronchospasm", "J45"],
    "sakit kepala sebelah": ["migraine", "migrain", "G43"],
    "migrain": ["migraine", "G43"],
    "kurang darah": ["anemia", "D64"],
    "parasetamol": ["acetaminophen", "paracetamol", "tylenol", "panadol"],
    "paracetamol": ["acetaminophen", "parasetamol"],
    "acetaminophen": ["paracetamol", "parasetamol", "tylenol"],
    "tylenol": ["acetaminophen", "paracetamol"],
    "panadol": ["acetaminophen", "paracetamol"],
    "advil": ["ibuprofen"],
    "motrin": ["ibuprofen"],
    "glucophage": ["metformin", "metformin hydrochloride"],
    "norvasc": ["amlodipine", "amlodipine besylate"],
    "zyrtec": ["cetirizine", "cetirizine hydrochloride"],
    "setirizin": ["cetirizine"],
    "claritin": ["loratadine"],
    "loratadin": ["loratadine"],
    "prilosec": ["omeprazole"],
    "pepcid": ["famotidine"],
    "imodium": ["loperamide", "loperamide hydrochloride"],
    "mucinex": ["guaifenesin"],
    "antasida": ["aluminum hydroxide", "magnesium hydroxide", "simethicone"],
    "mencret": ["diarrhea", "diare", "loperamide"],
    "diare": ["diarrhea", "loperamide"],
    "nyeri lutut": ["knee injuries", "cedera lutut"],
    "cedera lutut": ["knee injuries"],
    "susah tidur": ["sleep disorders", "insomnia"],
    "insomnia": ["sleep disorders"],
    "batuk berdahak": ["guaifenesin", "ambroxol", "bromhexine", "acetylcysteine", "bronchitis"],
    "batuk kering": ["dextromethorphan"],
    "pusing": ["migraine", "migrain", "cluster headache", "anemia", "hipertensi", "hypertension", "G43", "D64", "I10"],
    "pusying": ["pusing", "migraine", "migrain", "cluster headache", "anemia", "hipertensi"],
    "pening": ["pusing", "migraine", "migrain", "anemia"],
    "keliyengan": ["pusing", "anemia", "migraine"],
    "vertigo": ["migraine", "migrain", "pusing", "cluster headache"],
    "demam": ["influenza", "pneumonia", "tuberculosis", "urti"],
    "batuk": ["bronchitis", "pneumonia", "tuberculosis", "urti", "whooping cough"],
    "pilek": ["urti", "common cold", "allergic sinusitis", "rhinitis"],
    "sesak": ["asthma", "asma", "pneumonia", "bronchitis", "pulmonary embolism"],
    "mual": ["gerd", "gastritis"],
    "kembung": ["gastritis", "gerd"],
    "nyeri dada": ["angina", "pericarditis", "myocarditis", "gerd"],
    "setraline": ["sertraline", "sertraline hydrochloride"],
    "strln": ["sertraline", "sertraline hydrochloride"],
    "sertraline": ["sertraline hydrochloride", "zoloft", "antidepresan ssri"],
    "zoloft": ["sertraline"],
    "prozac": ["fluoxetine"],
    "fluoksetin": ["fluoxetine"],
    "escitalopram": ["escitalopram oxalate"],
    "amoksisilin": ["amoxicillin"],
    "amoxicillin": ["amoxicillin trihydrate", "antibiotik"],
    "azitromisin": ["azithromycin"],
    "sefiksim": ["cefixime"],
    "siprofloksasin": ["ciprofloxacin"],
    "asam mefenamat": ["mefenamic acid", "ponstan"],
    "ponstan": ["mefenamic acid"],
    "diklofenak": ["diclofenac sodium", "cataflam", "voltaren"],
    "natrium diklofenak": ["diclofenac sodium"],
    "cataflam": ["diclofenac"],
    "voltaren": ["diclofenac"],
    "sukralfat": ["sucralfate"],
    "lansoprazol": ["lansoprazole"],
    "domperidon": ["domperidone"],
    "ambroksol": ["ambroxol"],
    "salbutamol": ["albuterol", "ventolin", "inhaler asma"],
    "ventolin": ["salbutamol", "albuterol"],
    "albuterol": ["salbutamol"],
    "ctm": ["chlorpheniramine maleate", "alergi"],
    "kaptopril": ["captopril"],
    "kandesartan": ["candesartan"],
    "deksametason": ["dexamethasone"],
    "metilprednisolon": ["methylprednisolone"],
    "metronidazol": ["metronidazole"],
    "ketokonazol": ["ketoconazole"],
    "asiklovir": ["acyclovir"],
    "tablet tambah darah": ["ferrous sulfate", "zat besi", "anemia"],
    "zat besi": ["ferrous sulfate", "anemia"],
}

MEDICAL_TYPO_VOCAB: List[str] = [
    "diabetes", "mellitus", "hipertensi", "hypertension", "asma", "asthma",
    "pneumonia", "tuberkulosis", "tuberculosis", "anemia", "migraine", "migrain",
    "gastritis", "gerd", "bronkitis", "bronchitis", "influenza", "rhinitis",
    "sinusitis", "diare", "diarrhea", "paracetamol", "parasetamol", "acetaminophen",
    "ibuprofen", "cetirizine", "loratadine", "guaifenesin", "dextromethorphan",
    "omeprazole", "famotidine", "loperamide", "metformin", "amlodipine", "antasida",
    "sertraline", "fluoxetine", "escitalopram", "amitriptyline", "diazepam", "alprazolam",
    "gabapentin", "amoxicillin", "azithromycin", "cefixime", "ciprofloxacin", "metronidazole",
    "ketoconazole", "acyclovir", "mefenamic", "mefenamat", "diclofenac", "diklofenak",
    "meloxicam", "celecoxib", "ketorolac", "aspirin", "lansoprazole", "ranitidine",
    "sucralfate", "sukralfat", "domperidone", "ondansetron", "ambroxol", "ambroksol",
    "bromhexine", "acetylcysteine", "salbutamol", "albuterol", "chlorpheniramine",
    "fexofenadine", "pseudoephedrine", "glimepiride", "captopril", "candesartan",
    "bisoprolol", "simvastatin", "atorvastatin", "allopurinol", "furosemide",
    "dexamethasone", "methylprednisolone", "prednisone", "simethicone", "bisacodyl", "lactulose",
    "pusing", "vertigo", "pening", "demam", "batuk", "pilek", "sesak", "mual", "muntah",
    "kembung", "lemas", "gatal", "ruam", "kolesterol", "asam urat", "stroke", "jantung",
]


def _is_subsequence_match(query: str, target: str) -> bool:
    """True when a pure alphabetic abbreviated query (e.g. 'strln') matches target ('sertraline') in order."""
    q = (query or "").strip().lower()
    t = (target or "").strip().lower()
    if len(q) < 4 or not q.isalpha() or len(t) < len(q) or q[0] != t[0]:
        return False
    it = iter(t)
    return all(ch in it for ch in q)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s./-]", " ", (text or "").lower())).strip()


def _detect_language(norm_text: str) -> str:
    id_markers = {"apa", "itu", "yang", "saya", "obat", "penyakit", "gejala", "penyebabnya", "bedanya", "dan", "bagaimana", "tolong", "jelaskan", "untuk", "saat", "sakit", "nyeri", "lebih", "sederhana"}
    en_markers = {"what", "is", "are", "the", "causes", "symptoms", "treatment", "medication", "drug", "pain", "for"}
    words = set(norm_text.split())
    has_id = bool(words & id_markers)
    has_en = bool(words & en_markers)
    if has_id and has_en:
        return "mixed"
    return "id" if has_id else ("en" if has_en else "mixed")


def _detect_intent(norm_text: str) -> str:
    if any(w in norm_text for w in ("beda", "bedanya", "perbedaan", "dibanding", "compare", "vs")):
        return "disease_comparison"
    if any(w in norm_text for w in ("lebih sederhana", "jelaskan ulang", "maksudnya apa", "kurang paham", "singkat saja")):
        return "simplify_previous"
    if any(w in norm_text for w in ("obat", "dosis", "resep", "farmasi", "tablet", "kapsul", "sediaan", "zat aktif", "medication", "drug")):
        return "medication_info"
    if any(w in norm_text for w in ("rencana", "personalized plan", "buatkan plan", "revisi rencana", "revisi plan", "jadwal makan", "program")):
        if any(w in norm_text for w in ("revisi", "ubah", "perbarui", "ganti")):
            return "personalized_plan_revise"
        return "personalized_plan_create"
    if any(w in norm_text for w in ("progres", "perkembangan", "kemajuan", "riwayat catatan")):
        return "progress_review"
    if any(w in norm_text for w in ("penyebab", "kenapa", "mengapa", "penyebabnya")):
        return "follow_up_causes"
    if any(w in norm_text for w in ("gejala", "tanda", "cirinya", "gejalanya")):
        return "follow_up_symptoms"
    if any(w in norm_text for w in ("nyeri lutut", "keluhan saya", "cek gejala")):
        return "symptom_assessment"
    return "disease_info"


def understand_query(query: str) -> Dict[str, Any]:
    raw = (query or "").strip()
    norm = _normalize_text(raw)
    codes = re.findall(r"\b[A-Z]\d{2}(?:\.\d+)?\b", raw.upper())
    ndcs = re.findall(r"\b\d{4,5}-\d{3,4}(?:-\d{1,2})?\b", raw)

        # Conservative spelling normalization against domain vocabulary
    corrected_tokens: List[str] = []
    typo_corrections: List[str] = []
    for tok in norm.split():
        if len(tok) >= 4 and tok not in MEDICAL_TYPO_VOCAB:
            matches = difflib.get_close_matches(tok, MEDICAL_TYPO_VOCAB, n=1, cutoff=0.76)
            if matches and matches[0] != tok:
                corrected_tokens.append(matches[0])
                typo_corrections.append(f"{tok}->{matches[0]}")
                continue
        corrected_tokens.append(tok)
    corrected = " ".join(corrected_tokens)

    expansions: List[str] = []
    for phrase, syns in BILINGUAL_SYNONYMS.items():
        if re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", norm) or re.search(
            rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", corrected
        ):
            for s in syns:
                if s.lower() not in expansions:
                    expansions.append(s.lower())

    expanded_query = " ".join(
        dict.fromkeys([*corrected_tokens, *norm.split(), *expansions, *codes])
    ).strip()

    return {
        "original": raw,
        "normalized": norm,
        "corrected": corrected,
        "typo_corrections": typo_corrections,
        "expansions": expansions,
        "expanded_query": expanded_query,
        "codes": codes,
        "ndcs": ndcs,
        "language": _detect_language(norm),
        "intent": _detect_intent(norm),
    }


def _fts_query_string(text: str) -> str:
    tokens = [
        t for t in re.findall(r"[a-zA-Z0-9]+", text)
        if len(t) >= 3 and t.lower() not in QUERY_STOPWORDS
    ]
    if not tokens:
        return ""
    return " OR ".join(f'"{t}"*' for t in tokens[:14])


class HybridRAGRetriever:
    def __init__(self, store: Optional[RAGStore] = None, index: Optional[RAGVectorIndex] = None):
        self.store = store or RAGStore()
        self.index = index or RAGVectorIndex()

    def _ensure_index(self) -> None:
        if not self.index.is_ready and self.store.list_chunks():
            self.index.build_from_store(self.store)

    def search_diseases(
        self, query: str, *, limit: int = 10, offset: int = 0
    ) -> Dict[str, Any]:
        qi = understand_query(query)
        q_norm = qi["normalized"]
        q_corr = qi["corrected"]
        if not q_norm:
            all_items = self.store.list_diseases()
            return {
                "items": [self._disease_hit(d, 1.0, []) for d in all_items[offset : offset + limit]],
                "total": len(all_items),
                "query_info": qi,
                "ambiguous": False,
                "suggestions": [],
            }

        diseases = self.store.list_diseases()
        by_id = {d["id"]: d for d in diseases}
        scores: Dict[str, float] = {}
        matched_aliases_by_id: Dict[str, List[str]] = {}

        # 1. Exact & alias matching (canonical, Indonesian, English, ICD-10, synonyms, lay terms)
        for did, d in by_id.items():
            icd = (d.get("icd_code") or "").upper()
            names = [
                (d.get("canonical_name") or "", "canonical_name", 1.0),
                (d.get("indonesian_name") or "", "indonesian_name", 0.96),
                (d.get("english_name") or "", "english_name", 0.96),
            ]
            aliases = [*d.get("synonyms", []), *d.get("lay_terms", [])]
            best = 0.0
            hits: List[str] = []

            if icd and any(c == icd or icd.startswith(c) for c in qi["codes"]):
                best = max(best, 1.0)
                hits.append(f"ICD:{icd}")

            for val, _field, weight in names:
                v_low = val.lower()
                if not v_low:
                    continue
                if v_low == q_norm or v_low == q_corr:
                    best = max(best, weight)
                    hits.append(val)
                elif q_norm in v_low or q_corr in v_low:
                    best = max(best, weight * 0.85)
                    hits.append(val)

            for alias in aliases:
                a_low = alias.lower()
                if not a_low:
                    continue
                if a_low == q_norm or a_low == q_corr or a_low in qi["expansions"]:
                    best = max(best, 0.90)
                    if alias not in hits:
                        hits.append(alias)
                elif q_norm in a_low or (len(q_corr) >= 4 and q_corr in a_low):
                    best = max(best, 0.72)
                    if alias not in hits:
                        hits.append(alias)

            sym_text = (d.get("symptoms") or "").lower()
            desc_text = (d.get("short_description") or "").lower()
            for term in dict.fromkeys([q_norm, q_corr, *qi["expansions"]]):
                if len(term) >= 4 and (term in sym_text or term in desc_text):
                    best = max(best, 0.62)
                    if term not in hits:
                        hits.append(term)

            # Fuzzy similarity & subsequence tolerance on names, aliases, and single words
            name_pool = [d.get("canonical_name") or "", d.get("indonesian_name") or "", *aliases[:10]]
            word_pool = [w for cand in name_pool for w in re.split(r"[\s(),/-]+", cand) if len(w) >= 4]
            for candidate in [*name_pool, *word_pool]:
                if len(candidate) >= 4 and len(q_norm) >= 4:
                    c_low = candidate.lower()
                    ratio = difflib.SequenceMatcher(None, q_norm, c_low).ratio()
                    corr_ratio = difflib.SequenceMatcher(None, q_corr, c_low).ratio() if q_corr != q_norm else ratio
                    top_r = max(ratio, corr_ratio)
                    if top_r >= 0.74:
                        best = max(best, 0.68 * top_r)
                        if candidate not in hits:
                            hits.append(candidate)
                    elif _is_subsequence_match(q_norm, c_low):
                        best = max(best, 0.62)
                        if candidate not in hits:
                            hits.append(candidate)

            if best > 0:
                scores[did] = best
                matched_aliases_by_id[did] = hits[:4]

        # 2. FTS5 BM25 lexical search
        fts_q = _fts_query_string(qi["expanded_query"])
        if fts_q:
            with self.store._connect() as conn:
                try:
                    rows = conn.execute(
                        "SELECT id, bm25(diseases_fts) AS rank FROM diseases_fts WHERE diseases_fts MATCH ? ORDER BY rank LIMIT 20",
                        (fts_q,),
                    ).fetchall()
                    for pos, row in enumerate(rows):
                        did = row["id"]
                        lexical_score = 0.55 / (1.0 + 0.15 * pos)
                        scores[did] = max(scores.get(did, 0.0), lexical_score) + 0.20 * lexical_score
                except Exception:
                    pass

            # 3. Semantic chunk link boost (only when lexical/alias signal exists or very high semantic similarity)
            self._ensure_index()
            if self.index.is_ready:
                try:
                    for cid, sim in self.index.query(qi["expanded_query"], top_k=10):
                        if sim < 0.72:
                            continue
                        with self.store._connect() as conn:
                            row = conn.execute("SELECT entity_type, entity_id FROM knowledge_chunks WHERE chunk_id = ?", (cid,)).fetchone()
                            if row and row["entity_type"] == "disease" and row["entity_id"] in by_id:
                                did = row["entity_id"]
                                if did in scores or sim >= 0.85:
                                    scores[did] = scores.get(did, 0.0) + 0.45 * sim
                except Exception:
                    pass

        ranked = [
            (did, min(1.0, sc))
            for did, sc in scores.items()
            if sc >= MIN_ENTITY_SCORE and did in by_id
        ]
        ranked.sort(key=lambda x: x[1], reverse=True)

        paged = [
            self._disease_hit(by_id[did], round(sc, 3), matched_aliases_by_id.get(did, []))
            for did, sc in ranked[offset : offset + limit]
        ]
        ambiguous = len(ranked) > 1 and (ranked[0][1] - ranked[1][1]) < 0.08
        suggestions = [by_id[d]["canonical_name"] for d, _ in ranked[:3]] if ambiguous else []

        return {
            "items": paged,
            "total": len(ranked),
            "query_info": qi,
            "ambiguous": ambiguous,
            "suggestions": suggestions,
        }

    def search_medication_products(
        self, query: str, *, limit: int = 10, offset: int = 0
    ) -> Dict[str, Any]:
        qi = understand_query(query)
        q_norm = qi["normalized"]
        q_corr = qi["corrected"]
        if not q_norm:
            all_meds = self.store.list_medication_products()
            return {
                "items": [self._med_hit(m, 1.0, []) for m in all_meds[offset : offset + limit]],
                "total": len(all_meds),
                "query_info": qi,
            }

        meds = self.store.list_medication_products()
        by_id = {m["id"]: m for m in meds}
        scores: Dict[str, float] = {}
        matched_fields: Dict[str, List[str]] = {}

        search_terms = [t for t in dict.fromkeys([q_norm, q_corr, *qi["expansions"], *qi["ndcs"]]) if len(t) >= 2]

        for mid, m in by_id.items():
            best = 0.0
            hits: List[str] = []
            reg = (m.get("registration_number") or "").lower()
            pcode = (m.get("product_code") or "").lower()
            brand = (m.get("brand_name") or "").lower()
            generic = (m.get("generic_name") or "").lower()
            prod = (m.get("product_name") or "").lower()
            ings = [i.lower() for i in m.get("active_ingredients", [])]
            ind = (m.get("indications") or "").lower()

            for term in search_terms:
                if (reg and term == reg) or (pcode and term == pcode):
                    best = max(best, 1.0)
                    hits.append(f"BPOM/Barcode:{m.get('registration_number') or m.get('product_code')}")
                if reg and len(term) >= 5 and term in reg:
                    best = max(best, 0.96)
                    hits.append(f"NIE:{m.get('registration_number')}")
                if generic and (term == generic or term in generic):
                    w = 0.96 if term == generic else 0.85
                    best = max(best, w)
                    hits.append(f"generik:{m.get('generic_name')}")
                if brand and (term == brand or term in brand):
                    w = 0.95 if term == brand else 0.84
                    best = max(best, w)
                    hits.append(f"brand:{m.get('brand_name')}")
                for ing in ings:
                    if term == ing or term in ing:
                        best = max(best, 0.92 if term == ing else 0.82)
                        hits.append(f"zat_aktif:{ing}")
                if term in prod:
                    best = max(best, 0.80)
                if ind and term in ind:
                    best = max(best, 0.55)
                    hits.append("indikasi")

            # Combination match: multiple ingredients mentioned in query
            if len(ings) > 1:
                matched_ing_cnt = sum(1 for ing in ings if any(t in ing for t in q_corr.split() + qi["expansions"]))
                if matched_ing_cnt >= 2:
                    best = max(best, 0.97)
                    hits.append("kombinasi_zat_aktif")

            if len(q_norm) >= 4 and best < 0.7:
                word_cands = [w for fld in (generic, brand, prod, *ings) if fld for w in re.split(r"[\s(),/-]+", fld) if len(w) >= 4]
                for cand in [generic, brand, *ings, *word_cands]:
                    if cand and difflib.SequenceMatcher(None, q_norm, cand).ratio() >= 0.72:
                        best = max(best, 0.72)
                        hits.append(f"fuzzy:{cand}")
                    elif cand and _is_subsequence_match(q_norm, cand):
                        best = max(best, 0.68)
                        hits.append(f"cocok_huruf:{cand}")

            if best > 0:
                scores[mid] = best
                matched_fields[mid] = list(dict.fromkeys(hits))[:4]

        fts_q = _fts_query_string(qi["expanded_query"])
        if fts_q:
            with self.store._connect() as conn:
                try:
                    rows = conn.execute(
                        "SELECT id, bm25(medication_products_fts) AS rank FROM medication_products_fts WHERE medication_products_fts MATCH ? ORDER BY rank LIMIT 20",
                        (fts_q,),
                    ).fetchall()
                    for pos, row in enumerate(rows):
                        mid = row["id"]
                        lex = 0.50 / (1.0 + 0.15 * pos)
                        scores[mid] = max(scores.get(mid, 0.0), lex) + 0.15 * lex
                except Exception:
                    pass

        ranked = [
            (mid, min(1.0, sc))
            for mid, sc in scores.items()
            if sc >= MIN_ENTITY_SCORE and mid in by_id
        ]
        ranked.sort(key=lambda x: x[1], reverse=True)

        return {
            "items": [self._med_hit(by_id[mid], round(sc, 3), matched_fields.get(mid, [])) for mid, sc in ranked[offset : offset + limit]],
            "total": len(ranked),
            "query_info": qi,
        }

    def retrieve_evidence_chunks(
        self,
        query: str,
        *,
        entity_ids: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        top_k: int = 4,
    ) -> Dict[str, Any]:
        qi = understand_query(query)
        chunks = self.store.list_chunks()
        by_id = {c["chunk_id"]: c for c in chunks}
        if not chunks:
            return {"chunks": [], "evidence_sufficient": False, "query_info": qi}

        rrf_scores: Dict[str, float] = {}
        k_rrf = 30.0

        # 1. Exact entity link boost
        ent_set = set(entity_ids or [])
        if ent_set:
            for c in chunks:
                if c.get("entity_id") in ent_set:
                    rrf_scores[c["chunk_id"]] = rrf_scores.get(c["chunk_id"], 0.0) + 0.65

        # 2. FTS5 BM25 lexical ranking
        fts_q = _fts_query_string(qi["expanded_query"])
        if fts_q:
            with self.store._connect() as conn:
                try:
                    rows = conn.execute(
                        "SELECT chunk_id, bm25(knowledge_chunks_fts) AS rank FROM knowledge_chunks_fts WHERE knowledge_chunks_fts MATCH ? ORDER BY rank LIMIT 20",
                        (fts_q,),
                    ).fetchall()
                    for pos, row in enumerate(rows):
                        cid = row["chunk_id"]
                        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (k_rrf + pos + 1)
                except Exception:
                    pass

        # 3. Semantic vector ranking
        self._ensure_index()
        vec_sims: Dict[str, float] = {}
        if self.index.is_ready:
            try:
                vec_hits = self.index.query(qi["expanded_query"], top_k=20)
                for pos, (cid, sim) in enumerate(vec_hits):
                    vec_sims[cid] = sim
                    if sim >= 0.48:
                        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k_rrf + pos + 1)) + 0.42 * sim
            except Exception:
                pass

        # 4. Metadata filtering & alias/keyword reranking
        q_tokens = {
            t for t in qi["expanded_query"].lower().split()
            if len(t) >= 3 and t not in QUERY_STOPWORDS
        }
        scored: List[Tuple[float, Dict[str, Any]]] = []
        cat_set = set(categories or [])

        for cid, base_score in rrf_scores.items():
            c = by_id.get(cid)
            if not c:
                continue
            if cat_set and c.get("category") not in cat_set:
                continue
            title_low = c["title"].lower()
            content_low = c["content"].lower()
            aliases = " ".join(str(a).lower() for a in (c.get("metadata") or {}).get("aliases", []))
            exact_hits = sum(1 for t in q_tokens if t in title_low or t in aliases)
            body_hits = sum(1 for t in q_tokens if t in content_low)
            final_score = base_score + 0.08 * min(exact_hits, 4) + 0.03 * min(body_hits, 4)
            if final_score >= MIN_EVIDENCE_SCORE:
                scored.append((final_score, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_chunks = []
        for sc, c in scored[:top_k]:
            meta = c.get("metadata") or {}
            top_chunks.append(
                {
                    "chunk_id": c["chunk_id"],
                    "source_id": c["source_id"],
                    "source_name": c.get("source_name"),
                    "origin_url": meta.get("url") or c.get("source_origin_url"),
                    "verification_status": c.get("source_verification_status"),
                    "entity_type": c["entity_type"],
                    "entity_id": c.get("entity_id"),
                    "section_heading": c["section_heading"],
                    "title": c["title"],
                    "content": c["content"],
                    "category": c["category"],
                    "relevance_score": round(float(sc), 4),
                }
            )

        return {
            "chunks": top_chunks,
            "evidence_sufficient": len(top_chunks) > 0,
            "query_info": qi,
        }

    @staticmethod
    def _disease_hit(d: Dict[str, Any], score: float, matched_aliases: List[str]) -> Dict[str, Any]:
        return {
            **d,
            "matched_aliases": matched_aliases,
            "relevance_score": score,
        }

    @staticmethod
    def _med_hit(m: Dict[str, Any], score: float, matched_fields: List[str]) -> Dict[str, Any]:
        return {
            **m,
            "matched_fields": matched_fields,
            "relevance_score": score,
        }
