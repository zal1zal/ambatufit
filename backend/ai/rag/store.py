"""
Persisted SQLite + FTS5 Knowledge Store & Source Registry for AmbatuFit RAG.
Supports idempotent upserts, full provenance tracking, disease & medication
product indexing, narrative chunks, and ingestion run auditing.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional

RAG_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "rag"
DEFAULT_RAG_DB_PATH = RAG_DATA_DIR / "rag_store.sqlite"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class RAGStore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or DEFAULT_RAG_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS knowledge_sources (
                    source_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    publisher TEXT NOT NULL,
                    origin_url TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    language TEXT NOT NULL,
                    published_at TEXT,
                    updated_at TEXT,
                    fetched_at TEXT NOT NULL,
                    verification_status TEXT NOT NULL,
                    license_terms TEXT NOT NULL,
                    document_version TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active'
                );

                CREATE TABLE IF NOT EXISTS diseases (
                    id TEXT PRIMARY KEY,
                    canonical_name TEXT NOT NULL,
                    indonesian_name TEXT,
                    english_name TEXT,
                    synonyms_json TEXT NOT NULL DEFAULT '[]',
                    lay_terms_json TEXT NOT NULL DEFAULT '[]',
                    icd_code TEXT,
                    short_description TEXT,
                    causes TEXT,
                    symptoms TEXT,
                    risk_factors TEXT,
                    prevention_management TEXT,
                    source_references_json TEXT NOT NULL DEFAULT '[]',
                    review_metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS diseases_fts USING fts5(
                    id UNINDEXED,
                    canonical_name,
                    indonesian_name,
                    english_name,
                    synonyms,
                    lay_terms,
                    icd_code,
                    short_description,
                    symptoms
                );

                CREATE TABLE IF NOT EXISTS medication_products (
                    id TEXT PRIMARY KEY,
                    product_name TEXT NOT NULL,
                    brand_name TEXT,
                    generic_name TEXT,
                    active_ingredients_json TEXT NOT NULL DEFAULT '[]',
                    is_combination INTEGER NOT NULL DEFAULT 0,
                    strength TEXT,
                    dosage_form TEXT,
                    route TEXT,
                    marketing_authorization_holder TEXT,
                    registration_number TEXT,
                    product_code TEXT,
                    registration_status TEXT NOT NULL,
                    indications TEXT,
                    contraindications TEXT,
                    warnings TEXT,
                    interactions TEXT,
                    label_summary TEXT,
                    source_id TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (source_id) REFERENCES knowledge_sources(source_id)
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS medication_products_fts USING fts5(
                    id UNINDEXED,
                    product_name,
                    brand_name,
                    generic_name,
                    active_ingredients,
                    strength,
                    dosage_form,
                    registration_number,
                    indications
                );

                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT,
                    section_heading TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    language TEXT NOT NULL DEFAULT 'en',
                    category TEXT NOT NULL DEFAULT 'general_health',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    embedding_model TEXT,
                    embedding_dim INTEGER,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (source_id) REFERENCES knowledge_sources(source_id)
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunks_fts USING fts5(
                    chunk_id UNINDEXED,
                    title,
                    section_heading,
                    content,
                    category,
                    metadata_text
                );

                CREATE TABLE IF NOT EXISTS ingestion_runs (
                    run_id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    sources_count INTEGER NOT NULL DEFAULT 0,
                    diseases_count INTEGER NOT NULL DEFAULT 0,
                    medications_count INTEGER NOT NULL DEFAULT 0,
                    chunks_count INTEGER NOT NULL DEFAULT 0,
                    failures_json TEXT NOT NULL DEFAULT '[]'
                );
                """
            )

    def upsert_source(self, src: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_sources (
                    source_id, name, publisher, origin_url, source_type, language,
                    published_at, updated_at, fetched_at, verification_status,
                    license_terms, document_version, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    name=excluded.name,
                    publisher=excluded.publisher,
                    origin_url=excluded.origin_url,
                    source_type=excluded.source_type,
                    language=excluded.language,
                    published_at=excluded.published_at,
                    updated_at=excluded.updated_at,
                    fetched_at=excluded.fetched_at,
                    verification_status=excluded.verification_status,
                    license_terms=excluded.license_terms,
                    document_version=excluded.document_version,
                    status=excluded.status
                """,
                (
                    src["source_id"],
                    src["name"],
                    src["publisher"],
                    src["origin_url"],
                    src["source_type"],
                    src["language"],
                    src.get("published_at"),
                    src.get("updated_at"),
                    src["fetched_at"],
                    src["verification_status"],
                    src["license_terms"],
                    src["document_version"],
                    src.get("status", "active"),
                ),
            )

    def upsert_disease(self, rec: Dict[str, Any]) -> None:
        syns = rec.get("synonyms") or []
        lays = rec.get("lay_terms") or []
        refs = rec.get("source_references") or []
        rev = rec.get("review_metadata") or {}
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO diseases (
                    id, canonical_name, indonesian_name, english_name,
                    synonyms_json, lay_terms_json, icd_code, short_description,
                    causes, symptoms, risk_factors, prevention_management,
                    source_references_json, review_metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    canonical_name=excluded.canonical_name,
                    indonesian_name=COALESCE(excluded.indonesian_name, diseases.indonesian_name),
                    english_name=COALESCE(excluded.english_name, diseases.english_name),
                    synonyms_json=excluded.synonyms_json,
                    lay_terms_json=excluded.lay_terms_json,
                    icd_code=COALESCE(excluded.icd_code, diseases.icd_code),
                    short_description=COALESCE(excluded.short_description, diseases.short_description),
                    causes=COALESCE(excluded.causes, diseases.causes),
                    symptoms=COALESCE(excluded.symptoms, diseases.symptoms),
                    risk_factors=COALESCE(excluded.risk_factors, diseases.risk_factors),
                    prevention_management=COALESCE(excluded.prevention_management, diseases.prevention_management),
                    source_references_json=excluded.source_references_json,
                    review_metadata_json=excluded.review_metadata_json
                """,
                (
                    rec["id"],
                    rec["canonical_name"],
                    rec.get("indonesian_name"),
                    rec.get("english_name"),
                    json.dumps(syns, ensure_ascii=False),
                    json.dumps(lays, ensure_ascii=False),
                    rec.get("icd_code"),
                    rec.get("short_description"),
                    rec.get("causes"),
                    rec.get("symptoms"),
                    rec.get("risk_factors"),
                    rec.get("prevention_management"),
                    json.dumps(refs, ensure_ascii=False),
                    json.dumps(rev, ensure_ascii=False),
                ),
            )

    def upsert_medication_product(self, rec: Dict[str, Any]) -> None:
        ingredients = rec.get("active_ingredients") or []
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO medication_products (
                    id, product_name, brand_name, generic_name,
                    active_ingredients_json, is_combination, strength, dosage_form,
                    route, marketing_authorization_holder, registration_number,
                    product_code, registration_status, indications,
                    contraindications, warnings, interactions, label_summary,
                    source_id, source_url, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    product_name=excluded.product_name,
                    brand_name=excluded.brand_name,
                    generic_name=excluded.generic_name,
                    active_ingredients_json=excluded.active_ingredients_json,
                    is_combination=excluded.is_combination,
                    strength=excluded.strength,
                    dosage_form=excluded.dosage_form,
                    route=excluded.route,
                    marketing_authorization_holder=excluded.marketing_authorization_holder,
                    registration_number=excluded.registration_number,
                    product_code=excluded.product_code,
                    registration_status=excluded.registration_status,
                    indications=excluded.indications,
                    contraindications=excluded.contraindications,
                    warnings=excluded.warnings,
                    interactions=excluded.interactions,
                    label_summary=excluded.label_summary,
                    source_id=excluded.source_id,
                    source_url=excluded.source_url,
                    updated_at=excluded.updated_at
                """,
                (
                    rec["id"],
                    rec["product_name"],
                    rec.get("brand_name"),
                    rec.get("generic_name"),
                    json.dumps(ingredients, ensure_ascii=False),
                    1 if rec.get("is_combination") else 0,
                    rec.get("strength"),
                    rec.get("dosage_form"),
                    rec.get("route"),
                    rec.get("marketing_authorization_holder"),
                    rec.get("registration_number"),
                    rec.get("product_code"),
                    rec["registration_status"],
                    rec.get("indications"),
                    rec.get("contraindications"),
                    rec.get("warnings"),
                    rec.get("interactions"),
                    rec.get("label_summary"),
                    rec["source_id"],
                    rec["source_url"],
                    rec["updated_at"],
                ),
            )

    def upsert_chunk(self, chunk: Dict[str, Any]) -> None:
        meta = chunk.get("metadata") or {}
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_chunks (
                    chunk_id, source_id, entity_type, entity_id, section_heading,
                    title, content, language, category, metadata_json,
                    embedding_model, embedding_dim, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    source_id=excluded.source_id,
                    entity_type=excluded.entity_type,
                    entity_id=excluded.entity_id,
                    section_heading=excluded.section_heading,
                    title=excluded.title,
                    content=excluded.content,
                    language=excluded.language,
                    category=excluded.category,
                    metadata_json=excluded.metadata_json,
                    embedding_model=excluded.embedding_model,
                    embedding_dim=excluded.embedding_dim,
                    updated_at=excluded.updated_at
                """,
                (
                    chunk["chunk_id"],
                    chunk["source_id"],
                    chunk["entity_type"],
                    chunk.get("entity_id"),
                    chunk["section_heading"],
                    chunk["title"],
                    chunk["content"],
                    chunk.get("language", "en"),
                    chunk.get("category", "general_health"),
                    json.dumps(meta, ensure_ascii=False),
                    chunk.get("embedding_model"),
                    chunk.get("embedding_dim"),
                    chunk.get("updated_at") or utc_now_iso(),
                ),
            )

    def rebuild_fts_indexes(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM diseases_fts")
            for row in conn.execute("SELECT * FROM diseases").fetchall():
                syns = " ".join(json.loads(row["synonyms_json"] or "[]"))
                lays = " ".join(json.loads(row["lay_terms_json"] or "[]"))
                conn.execute(
                    "INSERT INTO diseases_fts (id, canonical_name, indonesian_name, english_name, synonyms, lay_terms, icd_code, short_description, symptoms) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        row["id"],
                        row["canonical_name"] or "",
                        row["indonesian_name"] or "",
                        row["english_name"] or "",
                        syns,
                        lays,
                        row["icd_code"] or "",
                        row["short_description"] or "",
                        row["symptoms"] or "",
                    ),
                )

            conn.execute("DELETE FROM medication_products_fts")
            for row in conn.execute("SELECT * FROM medication_products").fetchall():
                ings = " ".join(json.loads(row["active_ingredients_json"] or "[]"))
                conn.execute(
                    "INSERT INTO medication_products_fts (id, product_name, brand_name, generic_name, active_ingredients, strength, dosage_form, registration_number, indications) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        row["id"],
                        row["product_name"] or "",
                        row["brand_name"] or "",
                        row["generic_name"] or "",
                        ings,
                        row["strength"] or "",
                        row["dosage_form"] or "",
                        row["registration_number"] or "",
                        row["indications"] or "",
                    ),
                )

            conn.execute("DELETE FROM knowledge_chunks_fts")
            for row in conn.execute("SELECT * FROM knowledge_chunks").fetchall():
                meta = json.loads(row["metadata_json"] or "{}")
                meta_text = " ".join(
                    str(v) for vals in meta.values() for v in (vals if isinstance(vals, list) else [vals])
                )
                conn.execute(
                    "INSERT INTO knowledge_chunks_fts (chunk_id, title, section_heading, content, category, metadata_text) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        row["chunk_id"],
                        row["title"] or "",
                        row["section_heading"] or "",
                        row["content"] or "",
                        row["category"] or "",
                        meta_text,
                    ),
                )

    def update_chunk_embedding_meta(self, model_name: str, dim: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE knowledge_chunks SET embedding_model = ?, embedding_dim = ?",
                (model_name, dim),
            )

    def record_ingestion_run(self, run: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ingestion_runs (
                    run_id, mode, started_at, finished_at,
                    sources_count, diseases_count, medications_count, chunks_count, failures_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run["run_id"],
                    run["mode"],
                    run["started_at"],
                    run.get("finished_at") or utc_now_iso(),
                    run.get("sources_count", 0),
                    run.get("diseases_count", 0),
                    run.get("medications_count", 0),
                    run.get("chunks_count", 0),
                    json.dumps(run.get("failures") or [], ensure_ascii=False),
                ),
            )

    def clear_all_for_reindex(self, *, preserve_openfda: bool = False) -> None:
        with self._connect() as conn:
            if preserve_openfda:
                conn.executescript(
                    """
                    DELETE FROM knowledge_chunks WHERE source_id != 'SRC-OPENFDA-LABEL';
                    DELETE FROM medication_products WHERE source_id != 'SRC-OPENFDA-LABEL';
                    DELETE FROM diseases_fts;
                    DELETE FROM diseases;
                    """
                )
            else:
                conn.executescript(
                    """
                    DELETE FROM knowledge_chunks_fts;
                    DELETE FROM knowledge_chunks;
                    DELETE FROM medication_products_fts;
                    DELETE FROM medication_products;
                    DELETE FROM diseases_fts;
                    DELETE FROM diseases;
                    """
                )

    def list_sources(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM knowledge_sources ORDER BY source_id").fetchall()]

    def list_diseases(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            return [self._hydrate_disease(dict(r)) for r in conn.execute("SELECT * FROM diseases").fetchall()]

    def get_disease(self, disease_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM diseases WHERE id = ?", (disease_id,)).fetchone()
            return self._hydrate_disease(dict(row)) if row else None

    def list_medication_products(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            return [self._hydrate_med(dict(r)) for r in conn.execute("SELECT * FROM medication_products").fetchall()]

    def get_medication_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM medication_products WHERE id = ?", (product_id,)).fetchone()
            return self._hydrate_med(dict(row)) if row else None

    def list_chunks(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.*, s.name AS source_name, s.publisher AS source_publisher,
                       s.origin_url AS source_origin_url, s.verification_status AS source_verification_status
                FROM knowledge_chunks c
                JOIN knowledge_sources s ON c.source_id = s.source_id
                ORDER BY c.chunk_id
                """
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["metadata"] = json.loads(d.pop("metadata_json") or "{}")
                out.append(d)
            return out

    def inspect_source(self, source_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            src = conn.execute("SELECT * FROM knowledge_sources WHERE source_id = ?", (source_id,)).fetchone()
            chunks = conn.execute("SELECT chunk_id, title, section_heading, entity_type FROM knowledge_chunks WHERE source_id = ?", (source_id,)).fetchall()
            meds = conn.execute("SELECT id, product_name, generic_name FROM medication_products WHERE source_id = ?", (source_id,)).fetchall()
            return {
                "source": dict(src) if src else None,
                "chunks": [dict(c) for c in chunks],
                "medication_products": [dict(m) for m in meds],
            }

    def get_stats(self) -> Dict[str, Any]:
        with self._connect() as conn:
            counts = {
                "sources": conn.execute("SELECT COUNT(*) FROM knowledge_sources").fetchone()[0],
                "active_sources": conn.execute("SELECT COUNT(*) FROM knowledge_sources WHERE status = 'active'").fetchone()[0],
                "diseases": conn.execute("SELECT COUNT(*) FROM diseases").fetchone()[0],
                "medication_products": conn.execute("SELECT COUNT(*) FROM medication_products").fetchone()[0],
                "chunks": conn.execute("SELECT COUNT(*) FROM knowledge_chunks").fetchone()[0],
            }
            last_run = conn.execute("SELECT * FROM ingestion_runs ORDER BY started_at DESC LIMIT 1").fetchone()
            return {
                "counts": counts,
                "sources": self.list_sources(),
                "last_run": dict(last_run) if last_run else None,
            }

    @staticmethod
    def _hydrate_disease(d: Dict[str, Any]) -> Dict[str, Any]:
        d["synonyms"] = json.loads(d.pop("synonyms_json") or "[]")
        d["lay_terms"] = json.loads(d.pop("lay_terms_json") or "[]")
        d["source_references"] = json.loads(d.pop("source_references_json") or "[]")
        d["review_metadata"] = json.loads(d.pop("review_metadata_json") or "{}")
        return d

    @staticmethod
    def _hydrate_med(d: Dict[str, Any]) -> Dict[str, Any]:
        d["active_ingredients"] = json.loads(d.pop("active_ingredients_json") or "[]")
        d["is_combination"] = bool(d.get("is_combination"))
        return d

