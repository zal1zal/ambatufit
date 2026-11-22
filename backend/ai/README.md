# AmbatuFit AI Service (DDXPlus Baseline + Hybrid RAG + Conversational LLM Orchestration)

## Arsitektur & Batasan Kewenangan
Layanan inferensi AI ini berjalan **di luar STB** (laptop pengembang atau VM terpisah) agar beban CPU/RAM STB tetap aman (TST Slide 23), namun terhubung melalui API terautentikasi (`X-Service-Token`).

### 1. Sumber Dataset & Knowledge Registry (`backend/ai/rag/`)
- **DDXPlus Dataset (English)** — Figshare DOI [`10.6084/m9.figshare.22687585.v2`](https://doi.org/10.6084/m9.figshare.22687585) (`CC BY 4.0`, Fansi Tchango et al., NeurIPS 2022):
  - `release_train_patients.zip`: **1.025.602** baris (49 kondisi)
  - `release_validate_patients.zip`: **132.448** baris
  - `release_test_patients.zip`: **134.529** baris
  - `release_evidences.json`: **223** evidence resmi (`208` Binary `B`, `10` Categorical `C`, `5` Multi-choice `M`)
  - `release_conditions.json`: **49** kondisi medis resmi
- **MedlinePlus Health Topics Web Service (NLM NIH)** (`wsearch.nlm.nih.gov`): Edukasi penyakit & topik kesehatan berbahasa Inggris terstruktur.
- **openFDA Drug Label API (`api.fda.gov/drug/label.json`)**: Informasi label produk obat AS (*brand*, *generic*, zat aktif, bentuk sediaan, NDC). Dicatat dengan status `international_source_id_unverified` (bukan bukti izin edar BPOM Indonesia).
- **Aturan Internal AmbatuFit (`rules/health_guidance.json`)**: Panduan kebiasaan sehat umum berbasis dokumen domain.
- **Sumber Belum Aktif (Menunggu Kredensial/API Publik)**: `SRC-SATUSEHAT-KFA`, `SRC-BPOM-CEKPRODUK`, dan `SRC-WHO-ICD-API` terdaftar jujur sebagai `status="inactive"` di tabel `knowledge_sources`.

### 2. Retrieval-Augmented Generation (RAG) & Pretrained LLM (`backend/ai/llm_provider.py`)
- **Vector Index & Embedding (`ai/rag/embeddings.py`)**: Hybrid TF-IDF (word + char n-gram) tereduksi `TruncatedSVD` ter-normalisasi L2 (`local-multilingual-charword-lsa-v1`, 128 dimensi) + SQLite FTS5 BM25 + RRF reranking + exact entity/alias lookup (`rag_store.sqlite`).
- **Pretrained LLM Abstraction (`ai/llm_provider.py`)**: Mendukung `openai_compatible` (OpenAI/Groq/Ollama), `gemini`, `huggingface_api`, dan `huggingface_local` (`AutoTokenizer` + `AutoModelForCausalLM`) melalui environment variables `LLM_*`. Jika provider eksternal tidak dikonfigurasi, sistem secara jujur berjalan pada `generation_mode="grounded_extractive_fallback"` tanpa mengarang fakta atau klaim LLM eksternal.
- **Safety Gate & Pembatas Klinis**: Red-flag rule-based (`screening.py` & `detect_chat_red_flags`) selalu mendahului dan tidak dapat ditimpa oleh LLM maupun skor DDXPlus.

### 3. Cara Menjalankan Pipeline AI, Ingestion, Evaluasi, & Server (Off-STB)
```bash
cd backend

# 1. Ingestion Knowledge Base RAG (DDXPlus + MedlinePlus + openFDA + Internal Rules)
python -m ai.rag.ingest --mode init
python -m ai.rag.ingest --mode stats

# 2. Evaluasi Retrieval, Safety, & Conversational Memory
python -m ai.eval.run_evaluation

# 3. Latih & Evaluasi DDXPlus Multiclass Logistic Regression (bila perlu retrain)
python -m ai.train
python -m ai.evaluate

# 4. Jalankan server AI terautentikasi (port 8100, di luar STB)
python -m uvicorn ai.server:app --host 0.0.0.0 --port 8100
```

Hasil metrik evaluasi tercatat di `backend/ai/model_metadata.json`, `backend/ai/evaluation_report.txt`, dan `backend/ai/eval/evaluation_results.json`.
