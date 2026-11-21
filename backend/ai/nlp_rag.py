"""
Hybrid Bilingual NLP Concept Mapper + TF-IDF RAG Engine for AmbatuFit AI.
Maps free-text Indonesian/English complaints into verified DDXPlus evidences
plus non-DDXPlus wellness/symptom concepts, and retrieves grounded personalized
educational guidance from knowledge_base.json.
"""
from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ai.metadata import load_ddxplus_evidences
from ai.web_search import fetch_internet_health_knowledge

AI_DIR = Path(__file__).resolve().parent
KNOWLEDGE_BASE_PATH = AI_DIR / "knowledge_base.json"

# Indonesian translations for the most common DDXPlus evidence prompts (searchable in UI & NLP)
INDONESIAN_EVIDENCE_LABELS: Dict[str, str] = {
    "E_91": "Demam (terasa panas atau terukur termometer)",
    "E_94": "Menggigil atau meriang",
    "E_201": "Batuk",
    "E_77": "Batuk berdahak (dahak lebih banyak atau berwarna)",
    "E_203": "Serangan batuk hebat berulang",
    "E_45": "Batuk berdarah",
    "E_97": "Sakit atau nyeri tenggorokan",
    "E_181": "Hidung tersumbat atau pilek bening",
    "E_182": "Ingus atau lendir hidung berwarna kuning/kehijauan",
    "E_103": "Kehilangan indra penciuman (anosmia)",
    "E_169": "Hidung atau tenggorokan bagian belakang terasa gatal",
    "E_212": "Suara menjadi serak, berat, atau melemah",
    "E_14": "Nyeri dada bahkan saat sedang beristirahat",
    "E_66": "Sesak napas atau kesulitan bernapas signifikan",
    "E_64": "Sesak napas saat melakukan aktivitas ringan",
    "E_214": "Napas berbunyi mengi saat mengembuskan napas",
    "E_112": "Napas berbunyi mengi setelah batuk atau saat menarik napas",
    "E_128": "Sensasi tercekik tidak bisa bernapas atau berbicara",
    "E_53": "Merasakan nyeri pada salah satu bagian tubuh",
    "E_55": "Lokasi bagian tubuh yang terasa nyeri",
    "E_56": "Tingkat keparahan/intensitas nyeri (skala 0-10)",
    "E_54": "Karakteristik nyeri yang dirasakan",
    "E_148": "Mual atau terasa ingin muntah",
    "E_211": "Muntah berulang kali",
    "E_173": "Rasa panas/terbakar naik dari lambung ke tenggorokan (heartburn/asam lambung)",
    "E_30": "Perut terasa kembung atau penuh gas",
    "E_51": "Diare atau frekuensi buang air besar meningkat",
    "E_32": "Penurunan nafsu makan",
    "E_76": "Pusing ringan atau kepala terasa melayang",
    "E_82": "Pusing berputar atau terasa seperti akan pingsan",
    "E_89": "Lemas terus-menerus, mudah lelah, atau tidur tidak nyenyak",
    "E_88": "Sangat kelelahan hingga tidak mampu beraktivitas harian",
    "E_175": "Kelelahan baru, nyeri otot menyeluruh, atau kondisi fisik menurun",
    "E_144": "Nyeri otot atau pegal menyeluruh di berbagai bagian tubuh",
    "E_155": "Jantung berdebar cepat atau terasa tidak teratur (palpitasi)",
    "E_50": "Keringat keluar berlebihan (termasuk keringat dingin)",
    "E_129": "Ruam, kemerahan, atau kelainan kulit",
    "E_136": "Tingkat keparahan rasa gatal pada kulit",
    "E_170": "Rasa gatal berat pada mata",
    "E_127": "Mata berair berlebihan",
    "E_74": "Mata tampak merah merata",
    "E_42": "Kontak atau mengonsumsi pemicu alergi yang diketahui",
    "E_65": "Sulit atau sakit saat menelan makanan/minuman",
    "E_16": "Merasa cemas atau gelisah",
    "E_111": "Merasa ketakutan hebat seperti serangan panik",
    "E_124": "Riwayat asma atau penggunaan obat hirup bronkodilator",
    "E_125": "Riwayat didiagnosis GERD / penyakit asam lambung",
    "E_104": "Riwayat tekanan darah tinggi (hipertensi)",
    "E_69": "Riwayat diabetes",
    "E_79": "Kebiasaan merokok aktif",
    "E_99": "Riwayat migrain pribadi atau keluarga",
}

# Bilingual free-text phrase/keyword -> DDXPlus evidence entry mappings
FREE_TEXT_LEXICON: List[Tuple[Tuple[str, ...], List[Tuple[str, Any]], str]] = [
    (("demam", "panas badan", "suhu tinggi", "meriang", "fever", "high temp"), [("E_91", True)], "Demam / suhu tubuh meningkat"),
    (("menggigil", "chills", "shiver"), [("E_94", True)], "Menggigil"),
    (("batuk berdarah", "muntah darah", "hemoptysis", "coughing up blood", "darah saat batuk"), [("E_45", True), ("E_201", True)], "Batuk berdarah"),
    (("batuk berdahak", "berdahak", "dahak", "lendir", "sputum", "productive cough"), [("E_201", True), ("E_77", True)], "Batuk berdahak"),
    (("batuk", "cough", "batuk kering"), [("E_201", True)], "Batuk"),
    (("pilek", "ingus", "hidung meler", "hidung mampet", "hidung tersumbat", "flu", "common cold", "nasal congestion", "runny nose"), [("E_181", True)], "Pilek / hidung tersumbat"),
    (("ingus kuning", "ingus hijau", "lendir hijau", "lendir kuning"), [("E_182", True)], "Lendir hidung berwarna kuning/hijau"),
    (("tidak bisa mencium", "penciuman hilang", "anosmia", "loss of smell"), [("E_103", True)], "Penurunan penciuman"),
    (("bersin", "hidung gatal", "tenggorokan gatal", "itchy nose"), [("E_169", True)], "Bersin / hidung terasa gatal"),
    (("sakit tenggorokan", "radang tenggorokan", "nyeri tenggorokan", "tenggorokan sakit", "sore throat"), [("E_97", True), ("E_53", True), ("E_55", ["V_148"])], "Sakit tenggorokan"),
    (("sulit menelan", "sakit menelan", "susah menelan", "difficulty swallowing"), [("E_65", True)], "Nyeri atau sulit menelan"),
    (("suara serak", "suara hilang", "parau", "hoarse"), [("E_212", True)], "Suara serak"),
    (("sakit kepala", "nyeri kepala", "kepala sakit", "migrain", "migraine", "headache"), [("E_53", True), ("E_55", ["V_89", "V_166"]), ("E_56", 5)], "Sakit kepala / migrain"),
    (("pusing", "pening", "keliyengan", "kliyengan", "vertigo", "dizzy", "lightheaded"), [("E_76", True)], "Pusing / kepala terasa ringan"),
    (("mau pingsan", "hampir pingsan", "pusing berputar hebat", "about to faint"), [("E_82", True)], "Sensasi hampir pingsan"),
    (("nyeri dada", "dada sakit", "dada nyeri", "chest pain", "dada terasa tertekan"), [("E_14", True), ("E_53", True), ("E_55", ["V_101", "V_29"])], "Nyeri dada"),
    (("sesak napas", "sesak", "nafas pendek", "napas pendek", "susah bernapas", "sulit bernapas", "shortness of breath", "difficulty breathing"), [("E_66", True)], "Sesak napas"),
    (("mengi", "bengek", "napas berbunyi", "wheezing", "asma kambuh"), [("E_214", True)], "Napas berbunyi mengi"),
    (("tercekik", "suffocating", "tidak bisa bernapas"), [("E_128", True)], "Sensasi tercekik / sulit bernapas mendadak"),
    (("maag", "asam lambung", "gerd", "heartburn", "ulu hati panas", "dada panas", "perih di ulu hati"), [("E_173", True), ("E_53", True), ("E_55", ["V_197"])], "Gejala asam lambung / nyeri ulu hati"),
    (("nyeri ulu hati", "sakit lambung", "epigastric"), [("E_53", True), ("E_55", ["V_197"]), ("E_56", 5)], "Nyeri ulu hati"),
    (("mual", "eneg", "enek", "rasa ingin muntah", "nausea", "nauseous"), [("E_148", True)], "Mual"),
    (("muntah", "vomit", "muntah-muntah"), [("E_211", True)], "Muntah"),
    (("perut kembung", "begah", "penuh gas", "bloated"), [("E_30", True)], "Perut kembung"),
    (("diare", "mencret", "bab cair", "sering bab", "diarrhea"), [("E_51", True)], "Diare / BAB cair"),
    (("tidak nafsu makan", "hilang nafsu makan", "malas makan", "appetite"), [("E_32", True)], "Penurunan nafsu makan"),
    (("lemas", "lelah", "capek", "kelelahan", "letih", "lesu", "kurang tenaga", "fatigue", "tired"), [("E_89", True)], "Kelelahan / tubuh terasa lemas"),
    (("nyeri otot", "pegal", "pegal linu", "otot sakit", "badan pegal", "muscle pain"), [("E_144", True)], "Nyeri otot / pegal menyeluruh"),
    (("sakit punggung", "nyeri punggung", "nyeri pinggang", "back pain"), [("E_53", True), ("E_55", ["V_40"])], "Nyeri punggung / pinggang"),
    (("jantung berdebar", "berdebar-debar", "palpitasi", "detak jantung cepat", "palpitations"), [("E_155", True)], "Jantung berdebar / palpitasi"),
    (("keringat dingin", "keringat berlebih", "berkeringat deras", "sweating"), [("E_50", True)], "Keringat berlebihan / dingin"),
    (("ruam", "gatal-gatal", "bentol", "biduran", "kemerahan kulit", "rash", "itching"), [("E_129", True), ("E_136", 5)], "Ruam atau gatal pada kulit"),
    (("mata gatal", "itchy eyes"), [("E_170", True)], "Mata gatal"),
    (("mata merah", "red eyes"), [("E_74", True)], "Mata merah"),
    (("alergi", "reaksi alergi", "allergy"), [("E_42", True)], "Riwayat paparan / reaksi alergi"),
    (("cemas", "panik", "gelisah", "deg-degan cemas", "anxious", "panic"), [("E_16", True)], "Kecemasan / serangan panik"),
]

# General non-DDXPlus health & wellness concepts so users are never restricted to dataset vocabulary
WELLNESS_CONCEPTS: List[Tuple[Tuple[str, ...], str]] = [
    (("insomnia", "susah tidur", "sulit tidur", "begadang", "kurang tidur"), "Gangguan pola tidur / insomnia"),
    (("stres", "burnout", "banyak pikiran", "tertekan"), "Manajemen stres & beban pikiran"),
    (("doms", "habis olahraga", "setelah gym", "cedera ringan", "keseleo"), "Pemulihan pasca olahraga"),
    (("asam urat", "kolesterol", "gula darah", "tensi", "tekanan darah"), "Pemantauan parameter metabolik"),
    (("sariawan", "panas dalam", "bibir pecah", "kurang minum"), "Hidrasi & kesehatan rongga mulut"),
    (("gizi", "diet", "kalori", "protein", "makan apa", "menu"), "Perencanaan nutrisi personal"),
]

CONDITION_TRANSLATIONS: Dict[str, Tuple[str, str]] = {
    "URTI": ("Infeksi Saluran Napas Atas (ISPA Ringan)", "Keluhan ini sering berkaitan dengan infeksi virus ringan pada saluran napas atas seperti hidung dan tenggorokan."),
    "Influenza": ("Influenza (Flu)", "Kombinasi demam, batuk, lemas, dan nyeri tubuh yang lazim ditemukan pada infeksi virus musiman."),
    "Viral pharyngitis": ("Radang Tenggorokan Viral", "Iritasi tenggorokan akibat infeksi virus yang umumnya membaik dengan istirahat dan hidrasi cukup."),
    "Acute laryngitis": ("Radang Pita Suara Akut (Laringitis)", "Peradangan pita suara yang sering menimbulkan suara serak atau tenggorokan terasa tidak nyaman."),
    "Acute rhinosinusitis": ("Peradangan Hidung dan Sinus Akut", "Berkaitan dengan hidung tersumbat, ingus kental, atau rasa tertekan pada area wajah."),
    "Chronic rhinosinusitis": ("Peradangan Sinus Kronis", "Keluhan sinus dan hidung tersumbat yang menetap cukup lama dan perlu evaluasi dokter."),
    "Allergic sinusitis": ("Rhinitis atau Sinusitis Alergi", "Respons alergi pada saluran napas atas akibat paparan debu, serbuk sari, atau pemicu lainnya."),
    "Acute otitis media": ("Infeksi Telinga Tengah Akut", "Peradangan telinga tengah yang kerap menyertai infeksi saluran napas atas."),
    "GERD": ("Refluks Asam Lambung (GERD)", "Naiknya asam lambung ke kerongkongan yang memicu nyeri ulu hati atau rasa panas di dada."),
    "Bronchitis": ("Bronkitis Akut", "Peradangan saluran bronkus yang sering ditandai batuk menetap, kadang disertai dahak."),
    "Pneumonia": ("Pneumonia (Infeksi Paru)", "Infeksi jaringan paru yang memerlukan pemeriksaan langsung oleh dokter."),
    "Bronchospasm / acute asthma exacerbation": ("Penyempitan Saluran Napas atau Eksaserbasi Asma", "Perlu kewaspadaan medis apabila disertai bunyi napas mengi atau sesak napas."),
    "Acute COPD exacerbation / infection": ("Kekambuhan Penyakit Paru Obstruktif Kronis (PPOK)", "Perburukan keluhan napas pada saluran paru kronis yang perlu evaluasi tenaga medis."),
    "Tuberculosis": ("Tuberkulosis Paru (TBC)", "Infeksi paru jangka panjang yang perlu pemeriksaan dokter dan tes dahak secara langsung."),
    "Anemia": ("Kecenderungan Kurang Darah (Anemia)", "Dapat menimbulkan lemas, pusing, dan kulit tampak pucat; perlu dipastikan dengan pemeriksaan darah."),
    "Cluster headache": ("Sakit Kepala Klaster", "Pola nyeri kepala berat berulang di satu sisi yang sebaiknya dikonsultasikan ke dokter."),
    "Panic attack": ("Serangan Panik Akut", "Dapat memicu jantung berdebar, napas terasa pendek, dan rasa cemas yang intens."),
    "Possible NSTEMI / STEMI": ("Keluhan Jantung Prioritas Tinggi", "Segera cari pertolongan medis darurat atau ke IGD untuk evaluasi jantung secara langsung."),
    "Unstable angina": ("Nyeri Dada Prioritas Tinggi", "Membutuhkan pemeriksaan medis segera oleh dokter atau IGD."),
    "Stable angina": ("Nyeri Dada Terkait Aktivitas Fisik", "Perlu evaluasi dokter untuk memastikan kondisi pembuluh darah jantung Anda."),
    "Pulmonary embolism": ("Gangguan Pembuluh Paru Prioritas Tinggi", "Memerlukan evaluasi dokter sesegera mungkin di fasilitas kesehatan."),
    "Spontaneous pneumothorax": ("Paru-Paru Kolaps Spontan", "Keluhan nyeri dada dan sesak mendadak yang memerlukan pemeriksaan IGD segera."),
    "Pericarditis": ("Peradangan Selaput Jantung (Perikarditis)", "Nyeri dada yang sering membaik saat condong ke depan dan memerlukan evaluasi dokter."),
    "Myocarditis": ("Peradangan Otot Jantung (Miokarditis)", "Keluhan dada dan detak jantung setelah infeksi yang membutuhkan pemeriksaan dokter."),
    "Atrial fibrillation": ("Irama Jantung Tidak Teratur (Fibrilasi Atrium)", "Memerlukan pemeriksaan EKG oleh dokter untuk menilai irama jantung Anda."),
    "PSVT": ("Detak Jantung Sangat Cepat (PSVT)", "Gangguan irama jantung cepat mendadak yang perlu diperiksa tenaga medis."),
    "Anaphylaxis": ("Reaksi Alergi Berat (Anafilaksis)", "Kondisi gawat darurat medis yang membutuhkan penanganan segera di IGD."),
    "Whooping cough": ("Batuk Rejan (Pertusis)", "Serangan batuk panjang berulang yang memerlukan evaluasi dan penanganan dokter."),
    "Croup": ("Peradangan Saluran Napas Atas (Croup)", "Batuk keras khas dengan suara napas melengking yang memerlukan penilaian dokter."),
    "Epiglottitis": ("Peradangan Epiglotis", "Pembengkakan di tenggorokan atas yang membuat sulit menelan dan perlu evaluasi segera."),
    "Larygospasm": ("Kejang Pita Suara Mendadak", "Sensasi sulit menarik napas sesaat yang membutuhkan pemeriksaan medis."),
    "Bronchiectasis": ("Pelebaran Saluran Bronkus (Bronkiektasis)", "Batuk berdahak menahun yang memerlukan pemantauan dokter."),
    "Bronchiolitis": ("Infeksi Saluran Napas Kecil (Bronkiolitis)", "Peradangan saluran napas halus yang sering disertai mengi."),
    "Acute pulmonary edema": ("Penumpukan Cairan di Paru Akut", "Kondisi sesak berat yang memerlukan penanganan medis gawat darurat."),
    "Boerhaave": ("Cedera Kerongkongan Berat", "Muntah hebat disertai nyeri dada hebat merupakan kondisi darurat yang perlu segera ke IGD."),
    "Inguinal hernia": ("Hernia Lipat Paha", "Benjolan di area selangkangan yang perlu diperiksa langsung oleh dokter."),
    "Localized edema": ("Pembengkakan Lokal pada Anggota Tubuh", "Pembengkakan setempat pada bagian tubuh yang sebaiknya dievaluasi dokter untuk mengetahui penyebabnya."),
    "Guillain-Barré syndrome": ("Sindrom Guillain-Barre", "Kelemahan otot atau kesemutan simetris yang memerlukan evaluasi saraf segera."),
    "Myasthenia gravis": ("Kelemahan Otot (Miastenia Gravis)", "Kelemahan otot yang memberat dengan aktivitas dan perlu pemeriksaan dokter saraf."),
    "SLE": ("Lupus Eritematosus Sistemik", "Kondisi autoimun yang memerlukan konfirmasi pemeriksaan klinis dan laboratorium."),
    "Sarcoidosis": ("Sarkoidosis", "Peradangan jaringan tubuh yang penegakannya memerlukan evaluasi dokter."),
    "Pancreatic neoplasm": ("Gangguan Pankreas Kronis / Massa Pankreas", "Memerlukan evaluasi dokter serta pemeriksaan penunjang lanjutan."),
    "Pulmonary neoplasm": ("Gangguan Paru Jangka Panjang / Massa Paru", "Keluhan napas dan penurunan berat badan menetap perlu diperiksa langsung oleh dokter."),
    "Acute dystonic reactions": ("Reaksi Kaku Otot Akut (Distonia)", "Kekakuan atau kejang otot mendadak yang sering dipicu respons obat dan perlu ditangani tenaga medis."),
    "Chagas": ("Infeksi Parasit Kronis (Chagas)", "Membutuhkan konfirmasi tes laboratorium dan konsultasi dokter."),
    "Ebola": ("Infeksi Virus Berat (Ebola)", "Membutuhkan isolasi dan penanganan medis darurat segera."),
    "HIV (initial infection)": ("Infeksi Virus HIV Tahap Awal", "Gejala menyerupai flu berat dengan pembengkakan kelenjar yang hanya dapat dipastikan lewat tes laboratorium."),
    "Scombroid food poisoning": ("Reaksi Histamin Makanan (Scombroid)", "Reaksi kemerahan, gatal, atau mual setelah mengonsumsi ikan tertentu."),
    "Spontaneous rib fracture": ("Cedera atau Retak Tulang Rusuk", "Nyeri dada terlokalisir yang memburuk saat batuk atau menarik napas dalam dan perlu diperiksa dokter."),
}


@lru_cache(maxsize=1)
def load_knowledge_base() -> List[Dict[str, Any]]:
    if not KNOWLEDGE_BASE_PATH.exists():
        return []
    return json.loads(KNOWLEDGE_BASE_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _rag_vectorizer_index():
    docs = load_knowledge_base()
    if not docs:
        return [], None, None
    corpus = [
        " ".join(
            [
                d.get("title", ""),
                d.get("content", ""),
                " ".join(d.get("keywords", [])),
                " ".join(d.get("condition_codes", [])),
                " ".join(d.get("preference_tags", [])),
            ]
        ).lower()
        for d in docs
    ]
    vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
    matrix = vec.fit_transform(corpus)
    return docs, vec, matrix


def _get_indonesian_label(code: str, evidences: Optional[Dict[str, Any]] = None) -> str:
    if code in INDONESIAN_EVIDENCE_LABELS:
        return INDONESIAN_EVIDENCE_LABELS[code]
    ev_map = evidences if evidences is not None else load_ddxplus_evidences()
    spec = ev_map.get(code) or {}
    return (spec.get("question_id") or spec.get("question_en") or code).strip()


@lru_cache(maxsize=1)
def _evidence_tfidf_index():
    evidences = load_ddxplus_evidences()
    items = []
    corpus = []
    for code in sorted(evidences):
        spec = evidences[code]
        if spec.get("data_type") != "B":
            continue
        id_label = _get_indonesian_label(code, evidences)
        en_label = spec.get("question_en", "")
        items.append((code, id_label))
        corpus.append(f"{code} {id_label} {en_label}".lower())
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
    matrix = vec.fit_transform(corpus)
    return items, vec, matrix


def _token_pattern_hit(text: str, phrase: str) -> bool:
    escaped = re.escape(phrase.lower())
    return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text) is not None


def extract_evidences_from_text(
    text: str,
    *,
    ensure_non_empty: bool = False,
) -> Dict[str, Any]:
    """
    Flexibly extracts valid DDXPlus evidence entries AND general non-DDXPlus
    Indonesian wellness/symptom concepts from arbitrary user complaints.
    """
    raw_text = (text or "").strip()
    lower = raw_text.lower()
    evidences = load_ddxplus_evidences()

    selected: Dict[str, Any] = {}
    matched_descriptions: List[str] = []

    def _merge_entry(code: str, val: Any, desc: Optional[str] = None):
        if code not in evidences:
            return
        spec = evidences[code]
        dtype = spec.get("data_type")
        if dtype == "B":
            selected[code] = True
        elif dtype == "C":
            allowed = spec.get("possible-values", [])
            if val in allowed:
                selected[code] = val
        elif dtype == "M":
            allowed = set(spec.get("possible-values", []))
            vals = [v for v in (val if isinstance(val, list) else [val]) if v in allowed]
            if vals:
                existing = selected.get(code) if isinstance(selected.get(code), list) else []
                for v in vals:
                    if v not in existing:
                        existing.append(v)
                selected[code] = existing
        if desc and desc not in matched_descriptions:
            matched_descriptions.append(desc)

    # 1. Exact bilingual phrase matching (high precision)
    for triggers, mapped_entries, desc in FREE_TEXT_LEXICON:
        if any(_token_pattern_hit(lower, phrase) for phrase in triggers):
            for code, val in mapped_entries:
                _merge_entry(code, val, desc)

    # 2. Direct DDXPlus code mentions if typed by user (e.g. "E_91")
    for code_match in re.findall(r"\bE_\d+\b", raw_text.upper()):
        if code_match in evidences and evidences[code_match].get("data_type") == "B":
            _merge_entry(code_match, True, _get_indonesian_label(code_match, evidences))

    # 3. Character n-gram TF-IDF semantic matching for misspellings / English variants
    if raw_text and len(selected) < 2:
        items, vec, matrix = _evidence_tfidf_index()
        if matrix is not None:
            q_vec = vec.transform([lower])
            sims = cosine_similarity(q_vec, matrix).ravel()
            top_indices = np.argsort(sims)[::-1][:3]
            for idx in top_indices:
                if sims[idx] >= 0.24:
                    code, label = items[int(idx)]
                    if code not in selected:
                        _merge_entry(code, True, label)

    # 4. Recognize non-DDXPlus wellness & symptom concepts so user isn't limited to dataset terms
    general_concepts: List[str] = []
    for triggers, label in WELLNESS_CONCEPTS:
        if any(_token_pattern_hit(lower, phrase) for phrase in triggers):
            if label not in general_concepts:
                general_concepts.append(label)

    # 5. If user wants to proceed directly from arbitrary free text with no exact dataset match,
    # ground to general malaise/fatigue check-in (E_89=True) while keeping full free-text context.
    used_fallback = False
    if ensure_non_empty and not selected and raw_text:
        _merge_entry("E_89", True, "Keluhan umum / ketidaknyamanan fisik (catatan bebas)")
        used_fallback = True

    extracted_list = [
        {
            "evidence_code": code,
            "value": val,
            "label_id": _get_indonesian_label(code, evidences),
        }
        for code, val in selected.items()
    ]
    return {
        "evidence_entries": extracted_list,
        "matched_descriptions": matched_descriptions,
        "general_concepts": general_concepts,
        "used_general_fallback": used_fallback,
    }


def retrieve_rag_documents(
    query_text: str,
    *,
    profile: Optional[Dict[str, Any]] = None,
    condition_codes: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """
    Retrieves top-K grounded educational knowledge chunks using TF-IDF cosine similarity
    boosted by user profile goals, dietary/activity preferences, known conditions,
    and predicted condition patterns.
    """
    docs, vec, matrix = _rag_vectorizer_index()
    if not docs or vec is None or matrix is None:
        return []

    prof = profile or {}
    goal = (prof.get("health_goal") or "general_wellbeing").strip().lower()
    pref_tokens = {
        str(t).strip().lower()
        for key in ("dietary_preferences", "activity_preferences", "known_conditions")
        for t in (prof.get(key) or [])
        if str(t).strip()
    }
    cond_set = set(condition_codes or [])

    enriched_query = " ".join(
        [
            query_text or "",
            goal.replace("_", " "),
            " ".join(t.replace("_", " ") for t in pref_tokens),
            " ".join(cond_set),
        ]
    ).strip().lower()

    if enriched_query:
        sims = cosine_similarity(vec.transform([enriched_query]), matrix).ravel()
    else:
        sims = np.zeros(len(docs), dtype=float)

    scored: List[Tuple[float, Dict[str, Any], List[str]]] = []
    for idx, doc in enumerate(docs):
        if categories and doc.get("category") not in categories:
            continue
        score = float(sims[idx])
        reasons: List[str] = []
        if doc_conds := (set(doc.get("condition_codes", [])) & cond_set):
            score += 0.35
            reasons.append(f"terkait pola {', '.join(sorted(doc_conds))}")
        if goal in doc.get("goals", []):
            score += 0.14
            reasons.append(f"tujuan {goal}")
        if overlap := (set(t.lower() for t in doc.get("preference_tags", [])) & pref_tokens):
            score += 0.18
            reasons.append(f"preferensi {', '.join(sorted(overlap))}")
        if any(kw in (query_text or "").lower() for kw in doc.get("keywords", [])):
            score += 0.22
            reasons.append("sesuai kata kunci keluhan")
        if score > 0 or not enriched_query:
            scored.append((score, doc, reasons))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, doc, reasons in scored[:top_k]:
        results.append(
            {
                "doc_id": doc["doc_id"],
                "category": doc["category"],
                "title": doc["title"],
                "content": doc["content"],
                "reference_id": doc["reference_id"],
                "provider_id": doc.get("provider_id", "ambatufit"),
                "score": round(score, 4),
                "match_reasons": reasons,
            }
        )
    return results


def compose_assessment_narrative(
    *,
    predicted_condition: Optional[str],
    top_patterns: List[Dict[str, Any]],
    matched_evidence_codes: List[str],
    free_text_concepts: List[str],
    notes: Optional[str],
    duration_days: Optional[int],
    profile: Optional[Dict[str, Any]],
    monitoring_notes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Produces conversational, grounded Indonesian assessment output
    incorporating reported symptoms, free-text complaints, user profile, and reference guidance.
    """
    evidences = load_ddxplus_evidences()
    symptom_labels = [
        _get_indonesian_label(c, evidences)
        for c in matched_evidence_codes[:5]
    ]
    symptom_labels.extend(c for c in free_text_concepts if c not in symptom_labels)

    cond_id, cond_desc = CONDITION_TRANSLATIONS.get(
        predicted_condition or "",
        (
            f"Kondisi {predicted_condition}" if predicted_condition else "Keluhan Umum",
            "Keluhan Anda dirangkum berdasarkan kesamaan gejala dan panduan kesehatan umum.",
        ),
    )

    rag_query = " ".join(
        part
        for part in [
            notes or "",
            " ".join(symptom_labels),
            predicted_condition or "",
            " ".join(monitoring_notes or []),
        ]
        if part
    )
    rag_docs = retrieve_rag_documents(
        rag_query,
        profile=profile,
        condition_codes=[p["condition_code"] for p in top_patterns[:3]] if top_patterns else ([predicted_condition] if predicted_condition else []),
        top_k=3,
    )

    dur_text = f" selama {duration_days} hari" if duration_days else ""
    gejala_ringkas = ", ".join(symptom_labels[:4]) if symptom_labels else "keluhan yang Anda tulis"
    notes_excerpt = f" serta catatan tambahan ('{notes.strip()[:120]}')" if notes and notes.strip() else ""

    summary = (
        f"Berdasarkan keluhan {gejala_ringkas}{dur_text}{notes_excerpt}, "
        f"gambaran gejala Anda memiliki kemiripan dengan {cond_id}. "
        f"Ringkasan ini disajikan sebagai informasi awal dan bukan diagnosis medis pasti."
    )

    general_info: List[str] = [
        f"Gambaran Kondisi: {cond_desc}"
    ]
    if len(top_patterns) > 1:
        alt_names = [
            CONDITION_TRANSLATIONS.get(p["condition_code"], (p["condition_code"], ""))[0]
            for p in top_patterns[1:3]
        ]
        general_info.append(
            f"Kondisi lain yang juga memiliki kemiripan gejala: {', '.join(alt_names)}."
        )

    for doc in rag_docs:
        general_info.append(
            f"Panduan Perawatan ({doc['title']}): {doc['content']}"
        )

    prof = profile or {}
    goal = prof.get("health_goal")
    known = prof.get("known_conditions") or []
    diet = prof.get("dietary_preferences") or []
    act = prof.get("activity_preferences") or []
    personal_bits = []
    if goal:
        personal_bits.append(f"tujuan kesehatan ({goal})")
    if known:
        personal_bits.append(f"riwayat kondisi ({', '.join(known)})")
    if diet:
        personal_bits.append(f"preferensi makan ({', '.join(diet)})")
    if act:
        personal_bits.append(f"aktivitas ({', '.join(act)})")
    if monitoring_notes:
        personal_bits.append(f"catatan perkembangan terakhir ('{monitoring_notes[0][:70]}')")
    if personal_bits:
        general_info.append(
            f"Penyesuaian Profil: Saran di atas telah diselaraskan dengan {', '.join(personal_bits)} Anda."
        )

    follow_up: List[str] = [
        "Pantau suhu tubuh, kualitas istirahat, dan perubahan intensitas gejala dalam 24-48 jam ke depan melalui tab Perkembangan.",
        "Jaga hidrasi cukup dan terapkan panduan perawatan mandiri sesuai kategori keluhan di atas.",
    ]
    if duration_days and duration_days >= 3:
        follow_up.append(
            f"Karena keluhan sudah berlangsung {duration_days} hari, pertimbangkan konsultasi dokter apabila gejala tidak membaik atau memburuk."
        )
    else:
        follow_up.append(
            "Segera periksa ke tenaga kesehatan bila muncul sesak napas berat, nyeri dada hebat, demam tinggi menetap, atau gejala memburuk."
        )

    return {
        "summary": summary,
        "general_information": general_info,
        "follow_up_actions": follow_up,
        "rag_references": [
            {"doc_id": d["doc_id"], "title": d["title"], "reference_id": d["reference_id"]}
            for d in rag_docs
        ],
    }


def answer_personalized_rag_query(
    *,
    query: str,
    profile: Optional[Dict[str, Any]] = None,
    recent_assessments: Optional[List[Dict[str, Any]]] = None,
    recent_monitoring: Optional[List[Dict[str, Any]]] = None,
    safety_level: str = "none",
) -> Dict[str, Any]:
    """
    Conversational Q&A grounded in user profile, symptom assessments, monitoring logs,
    local guidelines, and live internet references. Strictly respects safety_level gates.
    """
    prof = profile or {}
    recent_assessments = recent_assessments or []
    recent_monitoring = recent_monitoring or []

    parsed = extract_evidences_from_text(query)
    context_pieces = [query]
    for a in recent_assessments[:2]:
        if a.get("summary"):
            context_pieces.append(str(a["summary"]))
    for m in recent_monitoring[:2]:
        if m.get("wellbeing_note"):
            context_pieces.append(str(m["wellbeing_note"]))

    rag_docs = retrieve_rag_documents(
        " ".join(context_pieces),
        profile=prof,
        top_k=3,
    )
    web_docs = fetch_internet_health_knowledge(query, max_items=1)

    safety_restricted = safety_level in ("urgent", "review_recommended")
    sections: List[str] = []

    goal_labels = {
        "general_wellbeing": "kesejahteraan umum",
        "balanced_nutrition": "nutrisi seimbang",
        "active_lifestyle": "gaya hidup aktif",
        "muscle_gain": "meningkatkan massa otot",
    }
    goal_raw = prof.get("health_goal") or "general_wellbeing"
    goal_txt = goal_labels.get(goal_raw, goal_raw)
    prefs = [
        *(prof.get("dietary_preferences") or []),
        *(prof.get("activity_preferences") or []),
    ]
    known = prof.get("known_conditions") or []

    header_bits = [f"tujuan {goal_txt}"]
    if prefs:
        header_bits.append(f"preferensi {', '.join(prefs)}")
    if known:
        header_bits.append(f"riwayat {', '.join(known)}")
    if recent_monitoring:
        header_bits.append(f"catatan terbaru ('{recent_monitoring[0].get('wellbeing_note', '')[:60]}')")

    sections.append(
        f"### Ringkasan Jawaban untuk Anda\n• Disusun sesuai {' dan '.join(header_bits)}."
    )

    if safety_restricted:
        sections.append(
            "### Peringatan Keselamatan\n• Karena masih terdapat riwayat keluhan yang perlu diperiksa, latihan fisik berat ditunda sementara hingga Anda berkonsultasi dengan dokter."
        )

    for doc in rag_docs:
        if safety_restricted and doc.get("category") == "physical_activity":
            continue
        bullets = [
            f"• {s.strip()}"
            for s in re.split(r"(?<=[.!?])\s+|\n+", doc["content"])
            if s.strip()
        ][:3]
        sections.append(f"### {doc['title']}\n" + "\n".join(bullets))

    for wdoc in web_docs:
        bullets = [
            f"• {s.strip()}"
            for s in re.split(r"(?<=[.!?])\s+|\n+", wdoc["content"])
            if s.strip()
        ][:3]
        sections.append(f"### Informasi Tambahan: {wdoc['title']}\n" + "\n".join(bullets))

    if parsed["general_concepts"] or parsed["matched_descriptions"]:
        topics = parsed["matched_descriptions"] + parsed["general_concepts"]
        sections.append(
            f"### Topik yang Dikenali\n• {', '.join(topics)}"
        )

    sections.append(
        "### Disclaimer\n• Informasi ini disajikan sebagai panduan edukasi kesehatan pribadi dan bukan pengganti pemeriksaan atau resep dokter."
    )

    sources_out = [
        {
            "doc_id": w["chunk_id"],
            "category": w["category"],
            "title": f"{w['title']} — {w['source_id']}",
            "reference_id": w["origin_url"],
            "match_reasons": ["referensi internet"],
        }
        for w in web_docs
    ]
    if not sources_out:
        sources_out = [
            {
                "doc_id": d["doc_id"],
                "category": d["category"],
                "title": d["title"],
                "reference_id": d["reference_id"],
                "match_reasons": d["match_reasons"],
            }
            for d in rag_docs
            if not (safety_restricted and d.get("category") == "physical_activity")
        ]

    return {
        "answer": "\n\n".join(sections),
        "safety_restricted": safety_restricted,
        "detected_evidences": parsed["evidence_entries"],
        "detected_concepts": parsed["matched_descriptions"] + parsed["general_concepts"],
        "retrieved_sources": sources_out,
    }
