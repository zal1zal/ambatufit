"""
Pretrained LLM Provider Abstraction, Prompt Engineering, Context Resolution,
Red-Flag Safety Priority Gate, and Citation Validator for AmbatuFit Off-STB AI Service.
"""
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
from dotenv import dotenv_values
import httpx

from ai.rag.retriever import HybridRAGRetriever
from ai.web_search import fetch_internet_health_knowledge

BACKEND_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

PROMPT_INJECTION_PATTERNS = (
    "abaikan instruksi",
    "abaikan aturan",
    "ignore previous instructions",
    "ignore all rules",
    "sekarang kamu dokter",
    "pretend you are a doctor",
    "berikan resep",
    "tentukan dosis pasti",
)

NSFW_REGEX = re.compile(
    r"\b(horny|sange|bokep|porno|pornografi|ngentot|colmek|coli|bugil|telanjang|kontol|memek|peju|toket|jilmek|pelacur|psk|hentai|onani)\b",
    re.I,
)

NSFW_PHRASES = (
    "open bo",
    "film dewasa",
    "video dewasa",
    "video panas",
    "foto syur",
    "bercinta yuk",
    "mau seks",
    "gairah seksual memuncak",
)

NON_HEALTH_PATTERNS = (
    "sakit hati",
    "patah hati",
    "putus cinta",
    "mantan pacar",
    "selingkuh",
    "galau",
    "bucin",
    "ditinggal nikah",
    "emotikon",
    "kode program",
    "pemrograman",
    "javascript",
    "python",
    "react native",
    "algoritma",
    "pemilu",
    "pilpres",
    "caleg",
    "partai politik",
    "skor bola",
    "piala dunia",
    "liga champions",
    "slot gacor",
    "judi online",
    "togel",
    "pinjol",
    "cryptocurrency",
    "bitcoin",
    "ramalan zodiak",
    "arti mimpi",
    "kunci gitar",
    "lirik lagu",
    "sinopsis film",
    "mobile legends",
    "valorant",
    "genshin",
)

HEALTH_TOPIC_TOKENS = (
    "sehat", "kesehatan", "sakit", "nyeri", "pusing", "pusying", "demam", "batuk", "pilek",
    "flu", "obat", "penyakit", "gejala", "dokter", "terapi", "tidur", "insomnia", "makan",
    "gizi", "nutrisi", "olahraga", "kebugaran", "skoliosis", "tulang", "otot", "sendi",
    "lambung", "maag", "gerd", "darah", "hipertensi", "tensi", "diabetes", "gula darah",
    "napas", "sesak", "asma", "alergi", "infeksi", "virus", "bakteri", "imun", "vitamin",
    "suplemen", "stres", "cemas", "panik", "depresi", "luka", "bengkak", "gatal", "ruam",
    "mual", "muntah", "diare", "sembelit", "kepala", "migrain", "perut", "dada", "jantung",
    "paru", "tbc", "pneumonia", "bronkitis", "ginjal", "hati", "liver", "kuning", "kulit",
    "mata", "telinga", "hidung", "tenggorokan", "gigi", "kaki", "tangan", "punggung", "pinggang",
    "leher", "bahu", "lutut", "kencing", "urin", "haid", "menstruasi", "hamil", "menyusui",
    "bayi", "lansia", "kolesterol", "asam urat", "anemia", "kalori", "protein", "diet",
    "berat badan", "obesitas", "bpom", "icd", "dosis", "efek samping", "antibiotik", "vaksin",
    "imunisasi", "fisioterapi", "rehabilitasi", "medis", "klinis", "diagnosis", "pencegahan",
    "penyebab", "penanganan", "pertolongan", "p3k", "dehidrasi", "oralit", "kompres",
)

ANAPHORA_MARKERS = (
    "penyebabnya",
    "gejalanya",
    "obatnya",
    "penanganannya",
    "pencegahannya",
    "komplikasinya",
    "mengatasinya",
    "mengobatinya",
    "tersebut",
    "tadi",
    "sebelumnya",
    "lebih sederhana",
    "tipe 1 dan tipe 2",
    "gejala yang umum",
    "bagaimana dengan obat",
)

RED_FLAG_CHAT_RULES: List[Tuple[str, Tuple[str, ...], str]] = [
    (
        "CHAT-RF-CHEST",
        ("nyeri dada", "dada ditekan", "dada terasa berat"),
        "Gejala nyeri dada—terutama bila disertai sesak napas, keringat dingin, atau menjalar ke lengan/rahang—termasuk tanda peringatan yang memerlukan pertolongan medis segera. Segera hubungi layanan gawat darurat (112/119) atau kunjungi IGD terdekat.",
    ),
    (
        "CHAT-RF-AIRWAY",
        ("tidak bisa bernapas", "susah bernapas berat", "tersedak tidak bisa bicara"),
        "Kesulitan bernapas berat atau rasa tercekik merupakan keadaan gawat darurat medis. Segera hubungi layanan darurat atau menuju IGD terdekat sekarang juga.",
    ),
    (
        "CHAT-RF-HEMOPTYSIS",
        ("batuk berdarah", "batuk darah"),
        "Keluhan batuk berdarah memerlukan evaluasi langsung oleh dokter sesegera mungkin di fasilitas kesehatan.",
    ),
    (
        "CHAT-RF-NEURO",
        ("pingsan", "kelemahan satu sisi", "wajah mencong", "bicara pelo"),
        "Penurunan kesadaran, kelemahan satu sisi tubuh, atau bicara mendadak pelo memerlukan evaluasi medis darurat segera di IGD terdekat.",
    ),
]


def _get_llm_config() -> Dict[str, Any]:
    env_file = dotenv_values(BACKEND_ENV_PATH) if BACKEND_ENV_PATH.exists() else {}

    def _val(key: str, default: str = "") -> str:
        v = os.environ.get(key)
        if v is not None and v.strip() != "":
            return v.strip()
        fv = env_file.get(key)
        return str(fv).strip() if fv is not None else default

    stops_raw = _val("LLM_STOP_SEQUENCES", "")
    return {
        "provider": _val("LLM_PROVIDER", "").lower(),
        "base_url": _val("LLM_BASE_URL", ""),
        "api_key": _val("LLM_API_KEY", ""),
        "model": _val("LLM_MODEL", ""),
        "timeout": float(_val("LLM_TIMEOUT_SECONDS", "20") or 20),
        "temperature": float(_val("LLM_TEMPERATURE", "0.3") or 0.3),
        "top_p": float(_val("LLM_TOP_P", "0.9") or 0.9),
        "top_k": int(float(_val("LLM_TOP_K", "40") or 40)),
        "max_tokens": int(float(_val("LLM_MAX_TOKENS", "768") or 768)),
        "repetition_penalty": float(_val("LLM_REPETITION_PENALTY", "1.08") or 1.08),
        "stop_sequences": [s for s in stops_raw.split("|") if s] if stops_raw else [],
    }


def get_public_llm_status() -> Dict[str, Any]:
    cfg = _get_llm_config()
    configured = bool(cfg["provider"] and cfg["model"] and (cfg["api_key"] or cfg["provider"] in ("ollama", "huggingface_local")))
    return {
        "llm_configured": configured,
        "provider": cfg["provider"] or "none",
        "model": cfg["model"] or None,
        "generation_params": {
            "temperature": cfg["temperature"],
            "top_p": cfg["top_p"],
            "top_k": cfg["top_k"],
            "max_tokens": cfg["max_tokens"],
            "repetition_penalty": cfg["repetition_penalty"],
        },
    }


def detect_chat_red_flags(message: str) -> Optional[Dict[str, str]]:
    lower = (message or "").lower()
    for rule_id, keywords, advice in RED_FLAG_CHAT_RULES:
        if rule_id == "CHAT-RF-CHEST":
            if any(k in lower for k in keywords) and any(
                extra in lower for extra in ("sesak", "keringat", "istirahat", "menjalar", "lengan")
            ):
                return {"rule_id": rule_id, "message": advice}
        elif any(k in lower for k in keywords):
            return {"rule_id": rule_id, "message": advice}
    return None


def detect_inappropriate_or_nsfw_query(message: str) -> bool:
    raw = (message or "").strip().lower()
    if not raw:
        return False
    if NSFW_REGEX.search(raw):
        return True
    return any(p in raw for p in NSFW_PHRASES)


def _has_health_signal(message: str) -> bool:
    lower = (message or "").strip().lower()
    if any(tok in lower for tok in HEALTH_TOPIC_TOKENS):
        return True
    if any(m in lower for m in ANAPHORA_MARKERS):
        return True
    return False


def detect_off_topic_query(
    message: str,
    *,
    has_active_context: bool = False,
    retriever: Optional[HybridRAGRetriever] = None,
) -> bool:
    lower = (message or "").strip().lower()
    if not lower:
        return True
    if any(p in lower for p in NON_HEALTH_PATTERNS):
        # Allow genuine physical emergency phrases even if text overlaps
        if not any(phys in lower for phys in ("nyeri dada", "sesak napas", "serangan jantung", "tekanan darah")):
            return True
    if _has_health_signal(lower):
        return False
    if has_active_context and any(
        lower.startswith(p) for p in ("apa penyebab", "apa gejala", "bagaimana dengan", "jelaskan", "bedanya")
    ):
        return False
    if retriever is not None:
        dis_hits = retriever.search_diseases(lower, limit=1).get("items") or []
        if dis_hits and (dis_hits[0].get("relevance_score") or 0.0) >= 0.48:
            return False
        med_hits = retriever.search_medication_products(lower, limit=1).get("items") or []
        if med_hits and (med_hits[0].get("relevance_score") or 0.0) >= 0.48:
            return False
    return True


def _looks_english(text: str) -> bool:
    words = re.findall(r"[a-zA-Z]+", (text or "").lower())
    if len(words) < 6:
        return False
    en_stops = sum(1 for w in words if w in {"the", "are", "is", "you", "your", "with", "that", "this", "have", "they", "what", "which", "may", "can", "pain", "headache", "phase"})
    id_stops = sum(1 for w in words if w in {"yang", "dan", "adalah", "pada", "untuk", "dengan", "dapat", "atau", "jika", "tidak", "gejala", "kondisi", "tubuh", "penyakit", "atau", "secara"})
    return en_stops >= 3 and en_stops > id_stops * 2


def resolve_conversational_query(
    message: str,
    *,
    history: List[Dict[str, str]],
    active_topic: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Rewrites elliptical/anaphoric Indonesian follow-ups ('Apa penyebabnya?', 'Jelaskan lebih sederhana',
    'Bagaimana dengan obatnya?') using conversation memory so RAG retrieves on the true topic.
    """
    raw = (message or "").strip()
    lower = raw.lower()
    if any(p in lower for p in NON_HEALTH_PATTERNS):
        return {
            "original_query": raw,
            "resolved_query": raw,
            "active_topic": None,
        }

    resolved = raw
    referenced_topic = active_topic

    # Try inferring active topic from recent user turns if not explicitly passed
    if not referenced_topic and history:
        for turn in reversed(history):
            if turn.get("role") == "user":
                txt = turn.get("content", "").strip()
                t_low = txt.lower()
                if (
                    txt
                    and not any(m in t_low for m in ("lebih sederhana", "penyebabnya", "obatnya"))
                    and not any(p in t_low for p in PROMPT_INJECTION_PATTERNS)
                    and not any(p in t_low for p in NON_HEALTH_PATTERNS)
                    and not detect_chat_red_flags(txt)
                    and not detect_inappropriate_or_nsfw_query(txt)
                ):
                    referenced_topic = txt
                    break

    follow_up_prefixes = ("apa penyebab", "apa gejala", "bagaimana dengan", "jelaskan lebih", "bedanya")
    if referenced_topic and (
        any(m in lower for m in ANAPHORA_MARKERS)
        or any(lower.startswith(p) for p in follow_up_prefixes)
    ):
        if referenced_topic.lower() not in lower:
            resolved = f"{referenced_topic} — {raw}"

    return {
        "original_query": raw,
        "resolved_query": resolved,
        "active_topic": referenced_topic,
    }


def build_chat_messages(
    *,
    user_query: str,
    intent: str,
    evidence_chunks: List[Dict[str, Any]],
    disease_hits: List[Dict[str, Any]],
    medication_hits: List[Dict[str, Any]],
    history: List[Dict[str, str]],
    summary: Optional[str] = None,
    profile_summary: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Builds concise, structured instruction prompt for external/local pretrained LLM."""
    evidence_lines: List[str] = []
    for idx, chk in enumerate(evidence_chunks, 1):
        evidence_lines.append(
            f"[E{idx} | {chk['source_id']} | {chk['title']} | url={chk.get('origin_url')}]\n{chk['content']}"
        )
    for idx, d in enumerate(disease_hits[:2], 1):
        evidence_lines.append(
            f"[D{idx} | Penyakit: {d.get('indonesian_name') or d['canonical_name']} | ICD:{d.get('icd_code')}] "
            f"Deskripsi: {d.get('short_description') or 'Tidak tersedia'}. Gejala: {d.get('symptoms') or 'Tidak tersedia'}."
        )
    for idx, m in enumerate(medication_hits[:2], 1):
        evidence_lines.append(
            f"[M{idx} | Produk: {m['product_name']} | Generik: {m.get('generic_name')} | Status: {m['registration_status']}] "
            f"Zat aktif: {', '.join(m.get('active_ingredients', []))}. Indikasi: {(m.get('indications') or 'Tidak tersedia')[:260]}. "
            f"Peringatan: {(m.get('warnings') or 'Tidak tersedia')[:220]}."
        )

    evidence_block = "\n\n".join(evidence_lines) if evidence_lines else "(TIDAK ADA EVIDENCE RELEVAN DITEMUKAN DI KNOWLEDGE BASE)"

    system_prompt = (
        "1. Role: Kamu adalah asisten informasi kesehatan AmbatuFit berbahasa Indonesia yang baku sesuai EYD/KBBI, ramah, ringkas, dan mudah dipahami siapa saja termasuk lansia.\n"
        f"2. Task: Jawab pertanyaan pengguna (intent terdeteksi: {intent}) sesuai kebutuhannya.\n"
        f"3. Context Profil Terotorisasi: {profile_summary or 'Tidak dikirim'}.\n"
        "4. Constraints: Gunakan HANYA fakta dari Evidence di bawah. DILARANG memberikan diagnosis pasti, meresepkan obat, menentukan dosis pribadi, mengarang nama obat, atau mencantumkan kode internal sistem (seperti [E1], [SRC-...], [Ref: ...]).\n"
        "5. Output Behavior: WAJIB format jawaban menjadi subjudul singkat (`### Judul`) diikuti poin-poin singkat (`• ...`). Hindari paragraf panjang.\n"
        "6. Clarification Behavior: Jika pertanyaan ambigu, ajukan 1 pertanyaan klarifikasi singkat.\n"
        "7. Source Behavior: Jangan tulis sumber jika berasal dari data internal. Jika menggunakan sumber internet, sebutkan secara alami tanpa tanda kurung siku [ ].\n\n"
        f"EVIDENCE:\n{evidence_block}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    if summary:
        messages.append({"role": "system", "content": f"Ringkasan percakapan sebelumnya: {summary}"})
    # Keep bounded short-term window (last 6 messages)
    for turn in history[-6:]:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_query})
    return messages


def _call_pretrained_llm(messages: List[Dict[str, str]], cfg: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    provider = cfg["provider"]
    if not provider or not cfg["model"]:
        return None, "not_configured"

    try:
        if provider in ("openai_compatible", "openai", "groq", "openrouter", "ollama"):
            base_url = cfg["base_url"] or (
                "http://127.0.0.1:11434/v1" if provider == "ollama" else "https://api.openai.com/v1"
            )
            headers = {"Content-Type": "application/json"}
            if cfg["api_key"]:
                headers["Authorization"] = f"Bearer {cfg['api_key']}"
            payload: Dict[str, Any] = {
                "model": cfg["model"],
                "messages": messages,
                "temperature": cfg["temperature"],
                "top_p": cfg["top_p"],
                "max_tokens": cfg["max_tokens"],
            }
            if cfg["stop_sequences"]:
                payload["stop"] = cfg["stop_sequences"]
            with httpx.Client(timeout=cfg["timeout"]) as client:
                res = client.post(f"{base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
                res.raise_for_status()
                text = res.json()["choices"][0]["message"]["content"]
                return text.strip(), f"llm_{provider}"

        if provider == "gemini":
            if not cfg["api_key"]:
                return None, "not_configured"
            sys_txt = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
            contents = [
                {
                    "role": "model" if m["role"] == "assistant" else "user",
                    "parts": [{"text": m["content"]}],
                }
                for m in messages
                if m["role"] != "system"
            ]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{cfg['model']}:generateContent?key={cfg['api_key']}"
            payload = {
                "systemInstruction": {"parts": [{"text": sys_txt}]},
                "contents": contents,
                "generationConfig": {
                    "temperature": cfg["temperature"],
                    "topP": cfg["top_p"],
                    "topK": cfg["top_k"],
                    "maxOutputTokens": cfg["max_tokens"],
                },
            }
            with httpx.Client(timeout=cfg["timeout"]) as client:
                res = client.post(url, json=payload)
                res.raise_for_status()
                cand = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                return cand.strip(), "llm_gemini"

        if provider == "huggingface_api":
            if not cfg["api_key"]:
                return None, "not_configured"
            base = cfg["base_url"] or f"https://api-inference.huggingface.co/models/{cfg['model']}"
            headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"}
            prompt_txt = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages) + "\nASSISTANT:"
            payload = {
                "inputs": prompt_txt,
                "parameters": {
                    "temperature": max(0.05, cfg["temperature"]),
                    "top_p": cfg["top_p"],
                    "top_k": cfg["top_k"],
                    "max_new_tokens": cfg["max_tokens"],
                    "repetition_penalty": cfg["repetition_penalty"],
                    "return_full_text": False,
                },
            }
            with httpx.Client(timeout=cfg["timeout"]) as client:
                res = client.post(base, json=payload, headers=headers)
                res.raise_for_status()
                data = res.json()
                text = data[0]["generated_text"] if isinstance(data, list) else data.get("generated_text", "")
                return text.strip(), "llm_huggingface_api"

        if provider == "huggingface_local":
            # Dynamic local Transformer execution via AutoTokenizer + AutoModelForCausalLM if installed
            from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore

            tok = AutoTokenizer.from_pretrained(cfg["model"])
            mdl = AutoModelForCausalLM.from_pretrained(cfg["model"])
            if hasattr(tok, "apply_chat_template") and tok.chat_template:
                enc = tok.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt")
                inputs = {"input_ids": enc}
            else:
                prompt_txt = "\n".join(f"{m['role']}: {m['content']}" for m in messages) + "\nassistant:"
                inputs = tok(prompt_txt, return_tensors="pt")
            out_ids = mdl.generate(
                **inputs,
                do_sample=True,
                temperature=cfg["temperature"],
                top_p=cfg["top_p"],
                top_k=cfg["top_k"],
                repetition_penalty=cfg["repetition_penalty"],
                max_new_tokens=cfg["max_tokens"],
            )
            gen_tokens = out_ids[0][inputs["input_ids"].shape[-1] :]
            return tok.decode(gen_tokens, skip_special_tokens=True).strip(), "llm_huggingface_local"
    except Exception:
        return None, "provider_error"

    return None, "not_configured"


def _to_bullet_points(text: str, *, limit: int = 4) -> List[str]:
    clean = re.sub(r"\*\*", "", text or "").strip()
    if not clean:
        return []
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", clean) if s.strip()]
    bullets: List[str] = []
    for sent in sentences[:limit]:
        s = sent.lstrip("•-* ").strip()
        if s:
            bullets.append(f"• {s}")
    return bullets


def _format_grounded_conversational_fallback(
    *,
    query: str,
    intent: str,
    active_topic: Optional[str],
    disease_hits: List[Dict[str, Any]],
    medication_hits: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
    history: List[Dict[str, str]],
) -> str:
    """
    Produces readable, structured Indonesian explanations with headings (`###`) and
    concise bullet points (`•`) strictly grounded in local & live web evidence.
    """
    if intent == "simplify_previous":
        prev_assistant = next(
            (h["content"] for h in reversed(history) if h.get("role") == "assistant"),
            None,
        )
        if prev_assistant:
            topic_label = active_topic or "topik sebelumnya"
            if disease_hits:
                d = disease_hits[0]
                lines = [f"### Penjelasan Sederhana: {d.get('indonesian_name') or d['canonical_name']}"]
                lines.extend(_to_bullet_points(d.get("short_description") or prev_assistant, limit=3))
                lines.append("• Gunakan informasi ini sebagai pemahaman awal dan diskusikan dengan dokter bila keluhan menetap.")
                return "\n".join(lines)
            if chunks:
                lines = [f"### Penjelasan Sederhana: {topic_label}"]
                lines.extend(_to_bullet_points(chunks[0]["content"], limit=3))
                return "\n".join(lines)

    if not chunks and not disease_hits and not medication_hits:
        return (
            "### Informasi Belum Ditemukan\n"
            "• Maaf, informasi yang Anda cari belum ditemukan pada referensi kesehatan kami maupun pencarian daring saat ini.\n"
            "• Coba perjelas nama kondisi atau nama zat aktif obat yang dimaksud.\n"
            "• Untuk kepastian medis, silakan berkonsultasi langsung dengan dokter atau apoteker."
        )

    sections: List[str] = []

    if intent == "medication_info":
        if medication_hits:
            m = medication_hits[0]
            ings = ", ".join(m.get("active_ingredients") or [])
            reg_note = (
                "Entri referensi luar negeri/edukatif; periksa nomor izin edar BPOM pada kemasan produk."
                if m.get("registration_status") != "verified_indonesia"
                else "Status registrasi Indonesia terverifikasi."
            )
            lines = [f"### Informasi Obat: {m['product_name']}"]
            lines.append(f"• Nama generik: {m.get('generic_name') or '-'}")
            if ings:
                lines.append(f"• Kandungan aktif: {ings}")
            if m.get("indications"):
                lines.extend(_to_bullet_points(f"Kegunaan umum: {m['indications'][:320]}", limit=2))
            if m.get("warnings"):
                lines.extend(_to_bullet_points(f"Hal yang perlu diperhatikan: {m['warnings'][:280]}", limit=2))
            lines.append(f"• Catatan izin edar: {reg_note}")
            lines.append("• Sistem tidak dapat menentukan dosis pribadi; tanyakan aturan pakai pasti kepada dokter atau apoteker.")
            sections.append("\n".join(lines))
        elif disease_hits:
            d = disease_hits[0]
            sections.append(
                f"### Informasi Obat untuk {d.get('indonesian_name') or d['canonical_name']}\n"
                "• Penentuan obat yang tepat dan dosis pribadi memerlukan pemeriksaan langsung oleh dokter.\n"
                "• Konsultasikan pilihan obat bebas atau obat resep kepada dokter maupun apoteker terdekat."
            )
    elif intent == "disease_comparison" and (disease_hits or chunks):
        d = disease_hits[0] if disease_hits else None
        name = (d.get("indonesian_name") or d["canonical_name"]) if d else (active_topic or "kondisi tersebut")
        lines = [f"### Perbandingan: {name}"]
        for c in chunks[:2]:
            lines.extend(_to_bullet_points(c["content"], limit=3))
        sections.append("\n".join(lines))
    elif intent == "follow_up_causes" and (chunks or disease_hits):
        topic = (disease_hits[0].get("indonesian_name") or disease_hits[0]["canonical_name"]) if disease_hits else (active_topic or "kondisi ini")
        lines = [f"### Penyebab & Latar Belakang: {topic}"]
        if disease_hits and disease_hits[0].get("causes"):
            lines.extend(_to_bullet_points(disease_hits[0]["causes"], limit=3))
        else:
            for c in chunks[:2]:
                lines.extend(_to_bullet_points(c["content"], limit=3))
        sections.append("\n".join(lines))
    elif intent == "follow_up_symptoms" and (disease_hits or chunks):
        d = disease_hits[0] if disease_hits else None
        name = (d.get("indonesian_name") or d["canonical_name"]) if d else (active_topic or "kondisi tersebut")
        lines = [f"### Gejala Umum: {name}"]
        if d and d.get("symptoms"):
            lines.extend(_to_bullet_points(d["symptoms"], limit=3))
        for c in chunks[:2]:
            lines.extend(_to_bullet_points(c["content"], limit=2))
        sections.append("\n".join(lines))
    else:
        if disease_hits:
            d = disease_hits[0]
            icd_txt = f" (Kode ICD-10: {d['icd_code']})" if d.get("icd_code") else ""
            lines = [f"### {d.get('indonesian_name') or d['canonical_name']}{icd_txt}"]
            if d.get("short_description"):
                lines.extend(_to_bullet_points(d["short_description"], limit=3))
            if d.get("symptoms") and d["symptoms"] not in (d.get("short_description") or ""):
                lines.extend(_to_bullet_points(f"Gejala yang sering muncul: {d['symptoms']}", limit=2))
            sections.append("\n".join(lines))
        for c in chunks[:3]:
            if c.get("language") == "en" or _looks_english(c.get("content") or ""):
                continue
            title_c = (c.get("title") or "").strip()
            heading_c = (c.get("section_heading") or "").strip()
            sec_title = f"{title_c} — {heading_c}" if title_c and heading_c and heading_c.lower() not in title_c.lower() else title_c
            if sec_title:
                lines = [f"### {sec_title}"]
                lines.extend(_to_bullet_points(c["content"], limit=3))
                sections.append("\n".join(lines))
            else:
                sections.append("\n".join(_to_bullet_points(c["content"], limit=3)))
        if len(disease_hits) > 1 and disease_hits[0]["relevance_score"] - disease_hits[1]["relevance_score"] < 0.08:
            alt = ", ".join(x.get("indonesian_name") or x["canonical_name"] for x in disease_hits[:3])
            sections.append(f"### Topik Terkait Lainnya\n• Terdapat beberapa topik serupa: {alt}. Topik mana yang ingin Anda bahas lebih lanjut?")

    sections.append(
        "### Disclaimer\n• Informasi ini bersifat edukasi kesehatan umum dan bukan pengganti pemeriksaan, diagnosis, atau resep dokter."
    )
    return "\n\n".join(sections)


class ConversationalOrchestrator:
    def __init__(self, retriever: Optional[HybridRAGRetriever] = None):
        self.retriever = retriever or HybridRAGRetriever()

    def handle_chat_turn(
        self,
        *,
        message: str,
        history: List[Dict[str, str]],
        active_topic: Optional[str] = None,
        summary: Optional[str] = None,
        profile_summary: Optional[str] = None,
        safety_level: str = "none",
    ) -> Dict[str, Any]:
        cfg = _get_llm_config()
        lower_msg = (message or "").lower()

        # 0. Inappropriate / 18+ NSFW boundary gate
        if detect_inappropriate_or_nsfw_query(message):
            return {
                "reply": (
                    "### Batasan Layanan Asisten Kesehatan\n"
                    "• Maaf, saya tidak dapat melayani atau menjawab pertanyaan yang mengandung unsur pornografi, asusila, atau konten 18+.\n"
                    "• Saya siap membantu pertanyaan edukasi seputar kesehatan fisik, mental, gejala penyakit, gaya hidup sehat, maupun informasi obat yang sopan."
                ),
                "intent": "inappropriate_refusal",
                "active_topic": active_topic,
                "safety_alert": False,
                "safety_rule_id": None,
                "citations": [],
                "evidence_sufficient": False,
                "generation_mode": "rule_based_safety_gate",
                "llm_provider": cfg["provider"] or "none",
                "llm_model": cfg["model"] or None,
                "clarification_needed": False,
                "suggested_entities": [],
            }

        # 1. Red-flag safety check takes absolute priority over LLM or search
        red_flag = detect_chat_red_flags(message)
        if red_flag:
            return {
                "reply": red_flag["message"],
                "intent": "red_flag_emergency",
                "active_topic": active_topic,
                "safety_alert": True,
                "safety_rule_id": red_flag["rule_id"],
                "citations": [],
                "evidence_sufficient": True,
                "generation_mode": "rule_based_safety_gate",
                "llm_provider": cfg["provider"] or "none",
                "llm_model": cfg["model"] or None,
                "clarification_needed": False,
                "suggested_entities": [],
            }

        # 2. Prompt injection / unsafe individual dosing refusal check
        injection_hit = any(p in lower_msg for p in PROMPT_INJECTION_PATTERNS)
        dosing_request = any(w in lower_msg for w in ("dosis untuk saya", "berapa mg harus saya minum", "resepkan obat", "obat resep apa yang harus"))
        if injection_hit or dosing_request:
            return {
                "reply": (
                    "Saya tidak dapat memberikan diagnosis klinis, menerbitkan resep, atau menentukan dosis obat individual maupun mengabaikan batasan keselamatan medis. "
                    "Saya tetap dapat membantu memberikan informasi edukatif umum berdasarkan referensi tepercaya atau mengarahkan Anda berkonsultasi dengan dokter atau apoteker."
                ),
                "intent": "safety_boundary_refusal",
                "active_topic": active_topic,
                "safety_alert": False,
                "safety_rule_id": None,
                "citations": [],
                "evidence_sufficient": True,
                "generation_mode": "rule_based_safety_gate",
                "llm_provider": cfg["provider"] or "none",
                "llm_model": cfg["model"] or None,
                "clarification_needed": False,
                "suggested_entities": [],
            }

        # 2b. Off-topic / non-health gate (prevents romantic/galau/coding/misc hallucinations & false history carry-over)
        if detect_off_topic_query(
            message,
            has_active_context=bool(active_topic or history),
            retriever=self.retriever,
        ):
            return {
                "reply": (
                    "### Pertanyaan di Luar Topik Kesehatan\n"
                    "• Maaf, saya tidak dapat menjawab pertanyaan tersebut karena berada di luar topik kesehatan.\n"
                    "• Silakan ajukan pertanyaan seputar gejala penyakit, kesehatan fisik maupun mental, pola hidup sehat, nutrisi, atau informasi obat."
                ),
                "intent": "off_topic_refusal",
                "active_topic": None,
                "safety_alert": False,
                "safety_rule_id": None,
                "citations": [],
                "evidence_sufficient": False,
                "generation_mode": "rule_based_scope_gate",
                "llm_provider": cfg["provider"] or "none",
                "llm_model": cfg["model"] or None,
                "clarification_needed": False,
                "suggested_entities": [],
            }

        # 3. Context resolution for multi-turn continuity
        ctx = resolve_conversational_query(message, history=history, active_topic=active_topic)
        resolved_q = ctx["resolved_query"]

        # 4. Hybrid RAG Retrieval (diseases, medications, and evidence chunks)
        chunk_res = self.retriever.retrieve_evidence_chunks(resolved_q, top_k=5)
        qi = chunk_res["query_info"]
        intent = qi["intent"]
        dis_res = self.retriever.search_diseases(resolved_q, limit=3)
        med_res = (
            self.retriever.search_medication_products(resolved_q, limit=3)
            if intent == "medication_info"
            else {"items": []}
        )

        disease_hits = dis_res["items"]
        medication_hits = med_res["items"]
        chunks = [c for c in chunk_res["chunks"] if c.get("language") != "en" and not _looks_english(c.get("content") or "")]

        # Enrich from live internet (Indonesian Wikipedia) when local evidence is empty or partial
        if not chunks or (not disease_hits and not medication_hits):
            web_chunks = fetch_internet_health_knowledge(resolved_q)
            if web_chunks:
                chunks = [*chunks, *web_chunks]

        next_topic = active_topic
        if intent not in ("simplify_previous",) and disease_hits:
            next_topic = disease_hits[0].get("indonesian_name") or disease_hits[0]["canonical_name"]
        elif intent == "medication_info" and medication_hits:
            next_topic = medication_hits[0].get("generic_name") or medication_hits[0]["product_name"]

        # 5. Build grounded prompt & invoke configured Pretrained LLM (if configured), else honest grounded fallback
        llm_messages = build_chat_messages(
            user_query=message,
            intent=intent,
            evidence_chunks=chunks,
            disease_hits=disease_hits,
            medication_hits=medication_hits,
            history=history,
            summary=summary,
            profile_summary=profile_summary,
        )
        llm_text, gen_mode = _call_pretrained_llm(llm_messages, cfg)
        if llm_text:
            reply = llm_text
        else:
            gen_mode = "grounded_extractive_fallback"
            reply = _format_grounded_conversational_fallback(
                query=message,
                intent=intent,
                active_topic=next_topic,
                disease_hits=disease_hits,
                medication_hits=medication_hits,
                chunks=chunks,
                history=history,
            )

        if safety_level in ("urgent", "review_recommended") and "tinjau" not in reply.lower():
            reply += "\n\nCatatan Keselamatan Akun: Anda memiliki riwayat keluhan yang memerlukan peninjauan tenaga profesional sebelum aktivitas fisik berat."

        # 6. Citation assembly & validation
        citations: List[Dict[str, Any]] = []
        seen_urls = set()
        for c in chunks:
            url = c.get("origin_url") or ""
            key = (c["source_id"], url or c["chunk_id"])
            if key not in seen_urls:
                seen_urls.add(key)
                citations.append(
                    {
                        "source_id": c["source_id"],
                        "title": c["title"],
                        "url": url,
                        "snippet": c["content"][:180],
                        "verification_status": c.get("verification_status") or "verified",
                    }
                )
        if not citations and disease_hits:
            for d in disease_hits[:1]:
                for ref in (d.get("source_references") or [])[:1]:
                    citations.append(
                        {
                            "source_id": ref.get("source_id") or "SRC-AMBATUFIT-RULES",
                            "title": ref.get("title") or (d.get("indonesian_name") or d["canonical_name"]),
                            "url": ref.get("url") or "",
                            "snippet": (d.get("short_description") or "")[:180],
                            "verification_status": "verified",
                        }
                    )
        if intent == "medication_info":
            for m in medication_hits[:2]:
                url = m.get("source_url") or ""
                key = (m["source_id"], url or m["id"])
                if key not in seen_urls:
                    seen_urls.add(key)
                    citations.append(
                        {
                            "source_id": m["source_id"],
                            "title": m["product_name"],
                            "url": url,
                            "snippet": (m.get("label_summary") or "")[:180],
                            "verification_status": m.get("registration_status") or "international_source_id_unverified",
                        }
                    )

        # Strip unverified URL hallucinations if LLM invented a URL not present in retrieved sources
        allowed_urls = {c["url"] for c in citations if c.get("url")}
        for found_url in re.findall(r"https?://[^\s)\]]+", reply):
            if found_url not in allowed_urls:
                reply = reply.replace(found_url, "[tautan tidak terverifikasi dihapus]")

        evidence_sufficient = bool(chunks or disease_hits or medication_hits)
        clarification_needed = bool(dis_res.get("ambiguous") or not evidence_sufficient)

        return {
            "reply": reply,
            "intent": intent,
            "active_topic": next_topic,
            "safety_alert": False,
            "safety_rule_id": None,
            "citations": citations[:5],
            "evidence_sufficient": evidence_sufficient,
            "generation_mode": gen_mode,
            "llm_provider": cfg["provider"] or "none",
            "llm_model": cfg["model"] or None,
            "clarification_needed": clarification_needed,
            "suggested_entities": dis_res.get("suggestions") or [],
        }


orchestrator = ConversationalOrchestrator()

