"""
Consistent Vector Embedding Index for AmbatuFit RAG.
Ensures index and query embeddings always share the exact same model identifier
and vector dimension, persisting to joblib alongside RAGStore.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import joblib
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import Normalizer

from ai.rag.store import RAG_DATA_DIR, RAGStore

DEFAULT_INDEX_PATH = RAG_DATA_DIR / "vector_index.joblib"
EMBEDDING_MODEL_ID = "local-multilingual-charword-lsa-v1"


class RAGVectorIndex:
    def __init__(self, index_path: Optional[Path] = None):
        self.index_path = Path(index_path or DEFAULT_INDEX_PATH)
        self.model_id: str = EMBEDDING_MODEL_ID
        self.dim: int = 0
        self.ids: List[str] = []
        self.vectors: Optional[np.ndarray] = None
        self.pipeline: Optional[Pipeline] = None
        self._load_if_exists()

    def _load_if_exists(self) -> None:
        if not self.index_path.exists():
            return
        try:
            payload = joblib.load(self.index_path)
            self.model_id = payload["model_id"]
            self.dim = int(payload["dim"])
            self.ids = list(payload["ids"])
            self.vectors = payload["vectors"]
            self.pipeline = payload["pipeline"]
        except Exception:
            self.ids = []
            self.vectors = None
            self.pipeline = None

    @property
    def is_ready(self) -> bool:
        return (
            self.pipeline is not None
            and self.vectors is not None
            and len(self.ids) > 0
            and self.vectors.shape[0] == len(self.ids)
            and self.vectors.shape[1] == self.dim
        )

    def build_from_store(self, store: RAGStore) -> Dict[str, Any]:
        chunks = store.list_chunks()
        if not chunks:
            self.ids = []
            self.vectors = None
            self.pipeline = None
            self.dim = 0
            return {"indexed": 0, "model_id": self.model_id, "dim": 0}

        texts: List[str] = []
        ids: List[str] = []
        for c in chunks:
            meta = c.get("metadata") or {}
            meta_str = " ".join(
                str(v)
                for vals in meta.values()
                for v in (vals if isinstance(vals, list) else [vals])
            )
            doc_text = f"{c['title']} {c['section_heading']} {c['content']} {c['category']} {meta_str}".lower()
            texts.append(doc_text)
            ids.append(c["chunk_id"])

        union = FeatureUnion(
            [
                ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True)),
                ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)),
            ]
        )
        tfidf_matrix = union.fit_transform(texts)
        max_rank = min(128, tfidf_matrix.shape[0] - 1, tfidf_matrix.shape[1] - 1)
        if max_rank >= 8:
            svd = TruncatedSVD(n_components=max_rank, random_state=42)
            norm = Normalizer(copy=False)
            reduced = norm.fit_transform(svd.fit_transform(tfidf_matrix))
            pipe = Pipeline([("features", union), ("svd", svd), ("norm", norm)])
            vectors = np.asarray(reduced, dtype=np.float32)
        else:
            norm = Normalizer(copy=False)
            vectors = np.asarray(norm.fit_transform(tfidf_matrix).toarray(), dtype=np.float32)
            pipe = Pipeline([("features", union), ("norm", norm)])

        self.model_id = EMBEDDING_MODEL_ID
        self.dim = int(vectors.shape[1])
        self.ids = ids
        self.vectors = vectors
        self.pipeline = pipe

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "model_id": self.model_id,
                "dim": self.dim,
                "ids": self.ids,
                "vectors": self.vectors,
                "pipeline": self.pipeline,
            },
            self.index_path,
        )
        store.update_chunk_embedding_meta(self.model_id, self.dim)
        return {"indexed": len(ids), "model_id": self.model_id, "dim": self.dim}

    def query(self, text: str, top_k: int = 12) -> List[Tuple[str, float]]:
        if not self.is_ready or not text or not text.strip():
            return []
        q_raw = self.pipeline.transform([text.lower()])
        q_vec = np.asarray(q_raw.toarray() if hasattr(q_raw, "toarray") else q_raw, dtype=np.float32)
        if q_vec.shape[1] != self.dim:
            raise ValueError(f"Embedding dimension mismatch: query {q_vec.shape[1]} != index {self.dim}")
        scores = (self.vectors @ q_vec[0]).ravel()
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [(self.ids[int(i)], float(scores[int(i)])) for i in top_idx if scores[int(i)] > 0.0]

