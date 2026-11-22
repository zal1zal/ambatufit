"""
Personalized Health Guidance Plan Service (DDD Core Subdomain Section 10.1):
Clean separation of concerns:
- Profile Retrieval (authorized user only)
- Completeness Check (ask instead of guessing)
- Rule-Based Safety Gate (precedence over everything; suppresses risky activity & AmbatuMove)
- Deterministic Personalization Rule Engine
- RAG Evidence Retrieval (only traceable sources)
- External API Enrichment (AmbatuNoutrish & AmbatuMove via IntegrationClient with graceful degradation)
- Plan Versioning, Activation, Revision & Unified Health Progress Tracking
"""
from datetime import datetime, timezone
import json
import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.clients.ai_client import ai_client
from app.clients.integration_client import integration_client
from app.contexts.personal_health_intelligence.guidance import generate_guidance
from app.contexts.personal_health_intelligence.repository import HealthRepository
from app.db import Assessment, MonitoringEntry, PersonalizedPlan
from app.schemas.rag_plan import (
    ChatCitationDTO,
    PersonalizedPlanDTO,
    PlanDraftRequest,
    PlanReviseRequest,
    PlanSectionActivityDTO,
    PlanSectionNutritionDTO,
    ProgressSummaryResponse,
)

INJURY_KEYWORDS = (
    "cedera",
    "nyeri lutut",
    "lutut",
    "keseleo",
    "terkilir",
    "bengkak",
    "nyeri sendi",
    "patah",
    "cedera otot",
    "knee injury",
    "skoliosis",
    "scoliosis",
    "saraf kejepit",
    "hnp",
    "nyeri punggung",
    "tulang belakang",
)

COMPLAINT_RECOVERY_PROTOCOLS: Dict[str, Dict[str, Any]] = {
    "skoliosis": {
        "keywords": ("skoliosis", "scoliosis", "tulang belakang bengkok", "kurva tulang"),
        "title": "Program Pemulihan Postur & Stabilisasi Skoliosis",
        "focus": "Memperkuat otot inti (core) dan paraspinal secara simetris, mengurangi ketegangan punggung tanpa membebani ruas tulang belakang, serta koreksi postur duduk dan tidur harian.",
        "habits": [
            ("Latihan Core Simetris & Peregangan Aman", "Lakukan gerakan Cat-Cow, Pelvic Tilt, Bird-Dog, dan Child's Pose perlahan 15 menit setiap pagi/sore. Hindari gerakan memutar (twisting) punggung secara cepat atau sit-up ekstrem."),
            ("Koreksi Ergonomi Duduk & Berdiri", "Pastikan kaki menapak rata di lantai, punggung tersandar menopang lekuk pinggang, layar sejajar pandangan mata, serta berdiri dan berjalan santai 3 menit setiap 45 menit duduk."),
            ("Hindari Beban Asimetris & Benturan Keras", "Tunda mengangkat beban berat sebelah, tas selempang berat di satu bahu, atau olahraga lompat benturan keras sebelum evaluasi dokter/fisioterapis."),
            ("Posisi Tidur Netral Tulang Belakang", "Tidur telentang dengan bantal tipis di bawah lutut, atau tidur miring dengan guling di antara lutut menggunakan kasur berpenopang rata."),
            ("Nutrisi Penunjang Tulang & Otot", "Penuhi asupan kalsium (susu rendah lemak, yoghurt, tempe, brokoli, ikan teri), vitamin D (sinar matahari pagi 15 menit, telur, ikan), serta protein harian yang cukup."),
        ],
        "daily_schedule": [
            ["06.30 - 07.00", "Peregangan Pagi Simetris", "Cat-Cow, Pelvic Tilt & Child's Pose 15 menit untuk mengendurkan otot punggung sebelum beraktivitas."],
            ["09.00 - 16.00", "Ergonomi Kerja / Belajar", "Duduk tegak simetris tanpa membungkuk; bangun dan peregangan bahu-leher ringan tiap 45 menit."],
            ["17.00 - 17.30", "Penguatan Core Tanpa Beban Berat", "Bird-Dog, Glute Bridge ringan, atau jalan santai / berenang gaya bebas ringan (hindari twisting & beban satu sisi)."],
            ["21.00 - 21.30", "Relaksasi & Tidur Netral", "Kompres hangat jika otot punggung terasa kaku; tidur telentang/miring dengan penyangga lutut."],
        ],
    },
    "nyeri_sendi": {
        "keywords": ("nyeri lutut", "lutut", "nyeri sendi", "sendi", "keseleo", "terkilir", "bengkak"),
        "title": "Program Pemulihan Sendi & Mobilitas Rendah Benturan",
        "focus": "Melindungi sendi yang nyeri dari benturan, meredakan kekakuan, dan memperkuat otot penyangga sendi secara bertahap.",
        "habits": [
            ("Pemanasan Sendi Tanpa Beban", "Lakukan gerakan ankle pump, mengencangkan paha perlahan (quad set), dan peregangan betis ringan selama 10 menit sebelum berjalan jauh."),
            ("Pilih Aktivitas Low-Impact", "Ganti lari atau lompat dengan jalan santai bertahap di jalur datar atau latihan ringan non-benturan; hentikan segera bila nyeri tajam muncul."),
            ("Kompres & Perlindungan Sendi", "Kompres dingin 15 menit jika sendi bengkak/hangat setelah aktivitas, atau kompres hangat di pagi hari bila terasa kaku."),
            ("Nutrisi Anti-Inflamasi & Jaringan", "Utamakan lauk kaya omega-3 dan protein (ikan kembung, sarden, tahu, tempe) serta jaga hidrasi minimal 2 liter air per hari."),
        ],
        "daily_schedule": [
            ["07.00 - 07.20", "Mobilitas Sendi Ringan", "Gerakan tekuk-lurus sendi perlahan tanpa beban di tempat tidur sebelum menumpu penuh."],
            ["12.00 - 13.00", "Nutrisi Pemulihan Jaringan", "Makan siang gizi seimbang tinggi protein & sayur; kurangi naik-turun tangga bila sendi masih nyeri."],
            ["16.30 - 17.00", "Latihan Stabilitas Ringan", "Jalan kaki santai 10-15 menit di permukaan rata atau peregangan otot paha dan betis."],
            ["20.30 - 21.00", "Evaluasi & Istirahat Sendi", "Tinggikan posisi tungkai sebentar jika terasa pegal dan catat skala nyeri di menu Perkembangan."],
        ],
    },
    "nyeri_punggung": {
        "keywords": ("nyeri punggung", "sakit pinggang", "pinggang", "hnp", "saraf kejepit"),
        "title": "Program Pemulihan Punggung & Dekompresi Ringan",
        "focus": "Mengurangi tekanan pada bantalan tulang belakang, menjaga kelenturan pinggang, dan memperbaiki teknik membungkuk.",
        "habits": [
            ("Teknik Mengangkat & Membungkuk Aman", "Tekuk lutut dan jaga punggung tetap lurus saat mengambil benda di lantai; hindari membungkuk langsung dari pinggang."),
            ("Peregangan Ringan & Jalan Singkat", "Lakukan jalan santai durasi 10 menit di permukaan rata serta peregangan lutut-ke-dada satu per satu secara perlahan bila nyaman."),
            ("Penopang Pinggang Saat Duduk", "Selipkan bantalan atau handuk gulung kecil di belakang pinggang bawah saat duduk lama dan ubah posisi tiap 40 menit."),
        ],
        "daily_schedule": [
            ["07.00 - 07.15", "Peregangan Punggung Lembut", "Napas diafragma 5 menit dilanjutkan gerakan pelvic tilt perlahan di matras."],
            ["10.00 - 15.00", "Jeda Berdiri Teratur", "Berdiri dan berjalan ringan 3 menit setiap jam duduk; hindari kursi terlalu rendah/empuk."],
            ["17.00 - 17.20", "Jalan Santai Pemulihan", "Jalan santai terukur 15-20 menit tanpa membawa barang berat."],
            ["21.00 - 21.30", "Istirahat Relaksasi Pinggang", "Berbaring telentang dengan betis disangga bantal selama 10 menit sebelum tidur."],
        ],
    },
    "lambung_gerd": {
        "keywords": ("maag", "gerd", "asam lambung", "ulu hati", "mual", "perut perih", "kembung"),
        "title": "Program Pemulihan Lambung & Kendali Asam Lambung",
        "focus": "Menjaga lambung tetap nyaman dengan makan porsi kecil teratur, menghindari pemicu asam, dan mengatur jarak waktu tidur.",
        "habits": [
            ("Pola Makan Porsi Kecil Lebih Sering", "Bagi makan menjadi 5-6 kali porsi kecil-sedang (sarapan, selingan pagi, makan siang, selingan sore, makan malam ringan) agar lambung tidak kosong terlalu lama maupun terlalu penuh."),
            ("Aturan Jeda Sebelum Berbaring", "Jangan langsung berbaring minimal 2-3 jam setelah makan, dan tinggikan bantal kepala-bahu sekitar 15 cm saat tidur."),
            ("Hindari Pemicu Iritasi Lambung", "Kurangi makanan sangat pedas, asam, gorengan berminyak tinggi, kopi pekat, cokelat, dan minuman bersoda."),
        ],
        "daily_schedule": [
            ["07.00 - 07.30", "Sarapan Lembut", "Bubur/oatmeal hangat atau nasi lembek dengan lauk kukus non-pedas."],
            ["10.30 & 15.30", "Selingan Penetral Lambung", "Pisang matang, pepaya, atau roti/biskuit gandum plain dan air putih suhu ruang."],
            ["12.30 & 18.30", "Makan Utama Terukur", "Porsi sedang rendah lemak; kunyah perlahan dan hindari minum terlalu banyak saat mengunyah."],
            ["21.30 - 22.00", "Tidur Posisi Miring Kiri", "Pastikan sudah berjeda minimal 2-3 jam dari makan malam dengan bantal sedikit ditinggikan."],
        ],
    },
    "hipertensi": {
        "keywords": ("hipertensi", "darah tinggi", "tekanan darah", "tensi"),
        "title": "Program Pengendalian Tekanan Darah (Pola DASH & Kardio Ringan)",
        "focus": "Membatasi asupan natrium, memperbanyak serat dan kalium alami, serta menjaga ritme olahraga aerobik ringan-sedang.",
        "habits": [
            ("Pembatasan Natrium Harian", "Kurangi garam dapur (< 1 sendok teh/hari), hindari makanan kaleng, daging olahan, keripik asin, serta kecap/penyedap berlebih."),
            ("Perbanyak Sumber Kalium & Serat", "Sertakan bayam, brokoli, pisang, pepaya, alpukat, atau tomat dalam menu harian kecuali ada pembatasan khusus dari dokter ginjal."),
            ("Aerobik Terukur & Napas Relaksasi", "Jalan cepat santai 25-30 menit 5 kali/minggu (hindari mengejan atau menahan napas saat mengangkat benda) serta latihan napas lambat sebelum tidur."),
        ],
        "daily_schedule": [
            ["06.30 - 07.00", "Jalan Santai Pagi", "25-30 menit aerobik ringan dengan napas teratur dan tetap nyaman diajak berbicara."],
            ["08.00 & 13.00", "Menu Rendah Garam (DASH)", "Lauk kukus/panggang bumbu rempah segar tanpa MSG/garam berlebih + 1 porsi sayur hijau."],
            ["16.30 - 17.00", "Hidrasi & Jeda Stres", "Istirahat 10 menit dengan teknik pernapasan lambat 4-7-8."],
            ["21.00 - 21.30", "Pantau Tensi & Tidur Cukup", "Catat keluhan/hasil pengukuran tensi bila punya alat di rumah dan tidur 7-8 jam."],
        ],
    },
    "diabetes": {
        "keywords": ("diabetes", "gula darah", "kencing manis", "glukosa"),
        "title": "Program Stabilisasi Gula Darah & Energi Harian",
        "focus": "Mencegah lonjakan gula darah lewat urutan makan berserat, karbohidrat terukur, dan jalan kaki ringan setelah makan.",
        "habits": [
            ("Urutan Makan Serat-Protein-Karbohidrat", "Dahulukan sayur berserat dan lauk berprotein sebelum nasi/karbohidrat kompleks untuk memperlambat penyerapan gula."),
            ("Stop Minuman & Camilan Bergula Tinggi", "Ganti minuman manis kemasan dengan air putih atau teh tawar, dan batasi gorengan tepung maupun kue manis."),
            ("Jalan Kaki 10-15 Menit Setelah Makan", "Berjalan santai di sekitar rumah sesudah makan siang dan malam membantu otot menyerap glukosa darah secara alami."),
        ],
        "daily_schedule": [
            ["07.00 - 07.30", "Sarapan Tinggi Serat & Protein", "Telur rebus/tahu/tempe + sayur tumis minim minyak + porsi karbohidrat kompleks terukur."],
            ["12.30 - 13.15", "Piring Gizi T & Jalan Ringan", "1/2 piring sayur, 1/4 lauk protein, 1/4 karbohidrat; disambung jalan santai 10-15 menit."],
            ["16.30 - 17.00", "Aktivitas Fisik Ringan", "Bersepeda santai, senam ringan, atau jalan kaki 20 menit."],
            ["20.30 - 21.30", "Periksa Kaki & Tidur Teratur", "Cek kebersihan dan kulit telapak kaki setiap malam dan jaga durasi tidur 7-8 jam."],
        ],
    },
    "pernapasan_asma": {
        "keywords": ("asma", "sesak", "bengek", "bronkitis", "batuk", "ispa", "pilek"),
        "title": "Program Pemulihan Napas & Ketahanan Saluran Pernapasan",
        "focus": "Menghindari pemicu iritasi saluran napas, melatih kontrol napas diafragma, dan menjaga hidrasi hangat.",
        "habits": [
            ("Kendali Debu & Pemicu Udara", "Bersihkan kamar dari debu, asap rokok, dan wewangian menyengat; gunakan masker bila beraktivitas di luar ruangan berdebu."),
            ("Latihan Napas Bibir Mengerucut", "Tarik napas pelan lewat hidung 4 detik dan embuskan lewat bibir mengerucut 6 detik selama 5-10 menit untuk melegakan aliran napas."),
            ("Hidrasi Hangat & Istirahat Suara", "Minum air putih hangat secara berkala untuk membantu mengencerkan lendir dan hindari minuman sangat dingin bila memicu batuk."),
        ],
        "daily_schedule": [
            ["06.30 - 06.45", "Latihan Napas Diafragma", "Duduk tegak di ruang berudara segar, lakukan teknik napas lambat 5-10 menit."],
            ["09.00 - 16.00", "Hidrasi Hangat & Hindari Asap", "Siapkan air minum hangat dan pastikan ventilasi ruang kerja baik."],
            ["17.00 - 17.20", "Gerak Ringan Terukur", "Jalan santai perlahan; hentikan segera bila terasa mengi atau dada sesak."],
            ["21.00 - 21.30", "Persiapan Kamar Tidur Bersih", "Pastikan sprei bebas debu dan tidur dengan posisi nyaman cukup 7-8 jam."],
        ],
    },
    "insomnia_stres": {
        "keywords": ("insomnia", "sulit tidur", "susah tidur", "stres", "cemas", "lemas", "kelelahan", "migrain", "sakit kepala"),
        "title": "Program Pemulihan Tidur, Relaksasi & Kejernihan Kepala",
        "focus": "Menstabilkan jam biologis tidur-bangun, menurunkan ketegangan otot leher-bahu, dan membatasi stimulan sore hari.",
        "habits": [
            ("Ritual Jam Tidur Konsisten", "Tidur dan bangun pada jam yang sama setiap hari serta dapatkan sinar matahari pagi 15 menit setelah bangun."),
            ("Bebas Kafein Setelah Pukul 14.00", "Hentikan kopi, teh kental, dan minuman berenergi setelah siang hari agar fase tidur dalam tidak terganggu."),
            ("Jeda Layar 60 Menit Sebelum Tidur", "Kurangi paparan gawai menjelang tidur dan lakukan peregangan leher-bahu lembut serta napas relaksasi 4-7-8."),
        ],
        "daily_schedule": [
            ["06.30 - 07.00", "Cahaya Pagi & Hidrasi Awal", "Minum segelas air putih dan jalan santai ringan 10-15 menit di luar ruangan."],
            ["14.00", "Batas Konsumsi Kafein", "Beralih ke air putih atau minuman hangat bebas kafein seperti air jahe hangat."],
            ["17.00 - 17.20", "Peregangan Leher & Bahu", "Lakukan peregangan bahu memutar perlahan 10 menit untuk melepas ketegangan kerja."],
            ["21.15 - 22.00", "Wind-Down Bebas Gawai", "Redupkan lampu, matikan notifikasi, dan lakukan napas relaksasi 5 menit sebelum tidur."],
        ],
    },
}

CLINICAL_DIET_CONDITIONS = {"diabetes", "hypertension", "kidney_disease", "gerd", "heart_disease"}

GOAL_LABELS = {
    "general_wellbeing": "Menjaga kesejahteraan dan kebugaran tubuh sehari-hari",
    "balanced_nutrition": "Mengelola pola makan bergizi seimbang sesuai preferensi",
    "active_lifestyle": "Membangun gaya hidup aktif yang aman dan terukur",
    "muscle_gain": "Mendukung peningkatan massa otot dan kecukupan asupan protein",
}


def _select_recovery_protocol(
    reported_complaint: Optional[str],
    user_note: Optional[str],
) -> Optional[Dict[str, Any]]:
    combined = f"{reported_complaint or ''} {user_note or ''}".strip()
    if not combined:
        return None
    low = combined.lower()
    for proto_key, proto in COMPLAINT_RECOVERY_PROTOCOLS.items():
        if any(kw in low for kw in proto["keywords"]):
            return {"key": proto_key, **proto}

    clean_topic = (reported_complaint or "").strip()
    if not clean_topic:
        return None
    short_label = clean_topic[:60].strip().capitalize()
    return {
        "key": "custom",
        "title": f"Program Pemulihan Terarah: {short_label}",
        "focus": f"Mengurangi keluhan '{short_label}' secara bertahap lewat penyesuaian aktivitas aman, nutrisi anti-radang & pemulihan jaringan, serta pemantauan gejala berkala.",
        "habits": [
            (
                f"Penyesuaian Aktivitas untuk {short_label}",
                f"Hindari aktivitas pemicu yang memperberat keluhan {short_label.lower()}; mulai gerak ringan bertahap 10-15 menit bila tubuh terasa nyaman.",
            ),
            (
                "Hidrasi & Nutrisi Pemulihan",
                "Penuhi kebutuhan air putih harian (minimal 2 liter), sayur hijau, buah segar, dan lauk berprotein seimbang untuk mendukung pemulihan jaringan tubuh.",
            ),
            (
                "Istirahat & Pemantauan Harian",
                f"Tidur 7-8 jam dan catat perubahan intensitas {short_label.lower()} setiap 1-2 hari di menu Perkembangan untuk bahan evaluasi dokter.",
            ),
        ],
        "daily_schedule": [
            ["07.00 - 07.20", "Mulai Hari Terukur", f"Peregangan lembut & hidrasi pagi; evaluasi kondisi {short_label.lower()} sebelum beraktivitas penuh."],
            ["12.00 - 13.00", "Nutrisi Gizi Seimbang", "Porsi sayur, protein (ikan/ayam/tempe/tahu), dan karbohidrat kompleks tanpa pemicu iritasi."],
            ["16.30 - 17.00", "Pemulihan Ringan", f"Aktivitas pemulihan ringan sesuai toleransi tubuh terhadap keluhan {short_label.lower()}."],
            ["21.00 - 21.30", "Evaluasi & Istirahat", f"Catat perkembangan keluhan {short_label.lower()} hari ini dan tidur berkualitas 7-8 jam."],
        ],
    }


def _compute_structured_nutrition_targets(
    goal: str,
    dietary_preferences: List[str],
    recovery_proto: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    prefs = set(dietary_preferences or [])
    if goal == "muscle_gain" or "high_protein" in prefs:
        kcal, prot, carbs, fat = 2350, 110, 280, 70
    elif goal == "active_lifestyle":
        kcal, prot, carbs, fat = 2200, 85, 275, 65
    elif goal == "balanced_nutrition":
        kcal, prot, carbs, fat = 2000, 75, 250, 60
    else:
        kcal, prot, carbs, fat = 2000, 65, 260, 60

    meals_per_day = 5 if (recovery_proto and recovery_proto.get("key") == "lambung_gerd") or "gastric_friendly" in prefs else 3
    portion_guide = [
        "1/2 piring sayur dan buah segar (serat, vitamin, mineral)",
        "1/4 piring lauk berprotein (ikan, ayam tanpa kulit, telur, tempe, atau tahu)",
        "1/4 piring karbohidrat kompleks (nasi merah/putih terukur, kentang, atau oatmeal)",
    ]
    if "low_salt" in prefs:
        portion_guide.append("Batasi garam tambahan (< 1 sendok teh/hari) dan hindari makanan olahan tinggi natrium.")
    if "low_sugar" in prefs:
        portion_guide.append("Hindari minuman manis kemasan; utamakan air putih minimal 8 gelas/hari.")
    if meals_per_day == 5:
        portion_guide.append("Bagi menjadi 3 makan utama porsi sedang + 2 selingan ringan ramah lambung.")

    return {
        "daily_calories_kcal": kcal,
        "protein_g": prot,
        "carbs_g": carbs,
        "fat_g": fat,
        "meals_per_day": meals_per_day,
        "portion_guide": portion_guide,
        "data_owner": "ambatufit:personal_health_intelligence",
        "master_food_provider": "ambatunoutrish",
    }


def _utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PlanService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = HealthRepository(db)

    def _to_dto(self, row: PersonalizedPlan) -> PersonalizedPlanDTO:
        snap = json.loads(row.profile_snapshot_json or "{}")
        nutr = json.loads(row.nutrition_section_json or "{}")
        act = json.loads(row.activity_section_json or "{}")
        cits = [ChatCitationDTO(**c) for c in json.loads(row.rag_citations_json or "[]")]
        goal_label = GOAL_LABELS.get(row.goal, row.goal)
        if snap.get("recovery_focus_title"):
            goal_label = f"{goal_label} ({snap['recovery_focus_title']})"
        return PersonalizedPlanDTO(
            id=row.id,
            version=row.version,
            parent_plan_id=row.parent_plan_id,
            status=row.status,
            goal=row.goal,
            goal_summary=goal_label,
            personalization_basis=snap,
            habits=json.loads(row.habits_json or "[]"),
            nutrition=PlanSectionNutritionDTO(**nutr),
            activity=PlanSectionActivityDTO(**act),
            safety_level=row.safety_level,
            safety_notes=json.loads(row.safety_notes_json or "[]"),
            rag_citations=cits,
            monitoring_guidance=json.loads(row.monitoring_guidance_json or "[]"),
            clarification_questions=json.loads(row.clarification_questions_json or "[]"),
            revision_reason=row.revision_reason,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def _build_plan_payload(
        self,
        user_id: str,
        *,
        goal_override: Optional[str],
        user_note: Optional[str],
        reported_complaint: Optional[str],
        nutrition_query: Optional[str],
        city: Optional[str],
    ) -> Tuple[str, str, Dict[str, Any], List[Dict[str, Any]], Dict[str, Any], Dict[str, Any], List[str], List[Dict[str, Any]], List[str], List[str], str]:
        # 1. Authorized profile & history retrieval
        profile = self.repo.get_or_create_profile(user_id)
        goal = goal_override or profile.health_goal or "general_wellbeing"

        # 2. Completeness check (never fabricate missing values)
        missing_fields: List[str] = []
        clarifications: List[str] = []
        if not profile.dietary_preferences:
            missing_fields.append("dietary_preferences")
            clarifications.append("Preferensi makanan Anda belum diisi (mis. tinggi protein, gizi seimbang, ramah lambung).")
        if not profile.activity_preferences:
            missing_fields.append("activity_preferences")
            clarifications.append("Jenis aktivitas fisik yang disukai belum diisi (mis. jalan kaki, bersepeda, latihan beban).")
        if profile.age_years is None:
            missing_fields.append("age_years")

        # 3. Safety Gate (assessments red-flags + injury complaint keywords + clinical conditions)
        urgent_asm = self.db.query(Assessment).filter(
            Assessment.user_id == user_id,
            Assessment.safety_level == "urgent",
        ).first()
        review_asm = self.db.query(Assessment).filter(
            Assessment.user_id == user_id,
            Assessment.safety_level == "review_recommended",
        ).first()

        complaint_lower = f"{reported_complaint or ''} {user_note or ''}".lower()
        has_injury = any(kw in complaint_lower for kw in INJURY_KEYWORDS)
        recovery_proto = _select_recovery_protocol(reported_complaint, user_note)

        safety_level = "none"
        safety_notes: List[str] = []
        status = "draft"

        if urgent_asm:
            safety_level = "urgent"
            status = "needs_review"
            safety_notes.append(
                urgent_asm.safety_message
                or "Terdapat indikator bahaya pada riwayat penilaian gejala Anda. Segera cari pertolongan medis dan tunda rencana aktivitas rutin."
            )
        elif review_asm or has_injury:
            safety_level = "review_recommended"
            status = "needs_review"
            if has_injury:
                if recovery_proto and recovery_proto.get("key") == "skoliosis":
                    safety_notes.append(
                        "Keluhan skoliosis/tulang belakang terdeteksi: hindari olahraga benturan keras atau beban asimetris sampai ditinjau dokter/fisioterapis; ikuti panduan postur & latihan stabilisasi ringan pada rencana di bawah."
                    )
                else:
                    safety_notes.append(
                        "Keluhan cedera/nyeri fisik terdeteksi: latihan atau aktivitas fisik yang berpotensi memperburuk keluhan ditunda sampai ditinjau tenaga profesional."
                    )
            if review_asm:
                safety_notes.append(
                    "Terdapat riwayat keluhan yang memerlukan peninjauan tenaga profesional sebelum menjalani aktivitas fisik."
                )

        known_lower = {k.strip().lower() for k in (profile.known_conditions or [])}
        if known_lower & CLINICAL_DIET_CONDITIONS:
            safety_notes.append(
                f"Kondisi tercatat ({', '.join(sorted(known_lower & CLINICAL_DIET_CONDITIONS))}): jangan gunakan rencana ini sebagai terapi nutrisi atau latihan medis khusus; konsultasikan ke dokter/ahli gizi."
            )

        # 4. Deterministic Personalization Rule Engine + Complaint Recovery Habits
        rule_items = generate_guidance(
            health_goal=goal,
            dietary_preferences=profile.dietary_preferences,
            activity_preferences=profile.activity_preferences,
            safety_level=safety_level,
        )
        default_readiness = "needs_review" if safety_level in ("urgent", "review_recommended") else "ready"
        habits: List[Dict[str, Any]] = []
        if recovery_proto:
            for idx, (h_title, h_desc) in enumerate(recovery_proto["habits"], 1):
                habits.append(
                    {
                        "id": f"rec-{recovery_proto['key']}-{idx}",
                        "category": "recovery",
                        "title": h_title,
                        "description": h_desc,
                        "readiness": default_readiness,
                        "reference_id": "SRC-AMBATUFIT-RULES",
                    }
                )
        for it in rule_items:
            if recovery_proto and len(habits) >= 7:
                break
            habits.append(
                {
                    "id": it.id,
                    "category": it.category,
                    "title": it.title,
                    "description": it.description,
                    "readiness": it.readiness,
                    "reference_id": it.source.reference_id,
                }
            )

        # 5. RAG Evidence Retrieval (general education & provenance only)
        rag_query_parts = [
            GOAL_LABELS.get(goal, goal.replace("_", " ")),
            "gizi seimbang nutrition aktivitas fisik exercise kebugaran",
            *(profile.dietary_preferences or []),
            *(profile.activity_preferences or []),
            reported_complaint or "",
            user_note or "",
        ]
        rag_chunks = await ai_client.retrieve_evidence_chunks(
            " ".join(p for p in rag_query_parts if p).strip(),
            categories=["nutrition", "physical_activity", "general_health", "general_wellbeing", "injury_safety"],
            top_k=4,
        )
        rag_citations = [
            {
                "source_id": c["source_id"],
                "title": c["title"],
                "url": c.get("origin_url") or "",
                "snippet": c["content"][:200],
                "verification_status": c.get("verification_status") or "verified",
            }
            for c in rag_chunks
        ]

        # 6. External API Retrieval (strict data minimization + graceful degradation)
        # Send ONLY sanitized food/goal keyword to AmbatuNoutrish; never symptoms/diagnosis.
        pref_food_query = nutrition_query or (
            profile.dietary_preferences[0].replace("_", " ")
            if profile.dietary_preferences
            else ("protein" if goal == "muscle_gain" else None)
        )
        if safety_level == "urgent":
            foods, food_status = [], "not_configured"
        else:
            foods, food_status = await integration_client.get_foods(query=pref_food_query)

        nutr_notes: List[str] = []
        if food_status == "available" and foods:
            nutr_notes.append("Data pilihan makanan dan kandungan gizi tersedia sesuai jadwal makan Anda.")
        elif food_status == "unavailable":
            nutr_notes.append("Layanan daftar makanan sedang tidak dapat dijangkau; ikuti panduan porsi gizi seimbang pada tabel di bawah.")
        else:
            nutr_notes.append("Daftar menu makanan mitra belum dihubungkan; ikuti panduan porsi makan bergizi seimbang pada tabel di bawah.")

        # AmbatuMove: NEVER called when safety_level restricts physical activity!
        if safety_level in ("urgent", "review_recommended"):
            gyms, gym_status = [], "unavailable"
            act_restricted = True
            if recovery_proto:
                act_notes = [
                    f"Olahraga berat/berdampak tinggi ditunda sementara selama pemulihan {recovery_proto['title'].lower()}; terapkan latihan aman & postur pada tabel jadwal harian di atas setelah meninjau saran dokter."
                ]
            else:
                act_notes = [
                    "Jadwal olahraga aktif ditunda sementara karena ada keluhan yang perlu diperiksakan ke dokter terlebih dahulu."
                ]
        else:
            act_restricted = False
            gyms, gym_status = await integration_client.get_gyms(city=city)
            act_notes = []
            if gym_status == "available" and gyms:
                act_notes.append("Lokasi fasilitas olahraga terdekat tersedia sesuai kota Anda.")
            elif gym_status == "unavailable":
                act_notes.append("Daftar tempat olahraga sedang tidak tersedia; Anda tetap dapat melakukan aktivitas ringan aman seperti jalan santai.")
            else:
                act_notes.append("Pencarian tempat olahraga belum terhubung; ikuti jadwal olahraga ringan yang aman pada tabel harian.")

        monitoring_guidance = [
            "Catat keluhan, tingkat nyeri/kelelahan, atau kebiasaan makan dan tidur Anda di tab Perkembangan setiap 1-3 hari.",
            "Lakukan revisi rencana jika tujuan kesehatan, preferensi makanan/olahraga, atau kondisi tubuh berubah.",
        ]

        profile_snapshot: Dict[str, Any] = {
            "user_id": user_id,
            "age_years": profile.age_years,
            "health_goal": goal,
            "dietary_preferences": profile.dietary_preferences,
            "activity_preferences": profile.activity_preferences,
            "known_conditions": profile.known_conditions,
            "missing_fields": missing_fields,
            "reported_complaint": reported_complaint,
        }
        if recovery_proto:
            profile_snapshot["recovery_focus_title"] = recovery_proto["title"]
            profile_snapshot["recovery_focus"] = recovery_proto["focus"]
            profile_snapshot["daily_schedule"] = recovery_proto["daily_schedule"]
        nutr_targets = _compute_structured_nutrition_targets(
            goal=goal,
            dietary_preferences=profile.dietary_preferences,
            recovery_proto=recovery_proto,
        )
        nutr_section = {
            "provider": "ambatunoutrish",
            "provider_status": food_status,
            "targets": nutr_targets,
            "items": foods,
            "guidance_notes": nutr_notes,
        }
        act_section = {
            "provider": "ambatumove",
            "provider_status": gym_status,
            "restricted_by_safety": act_restricted,
            "gyms": gyms,
            "guidance_notes": act_notes,
        }

        return (
            goal,
            status,
            profile_snapshot,
            habits,
            nutr_section,
            act_section,
            safety_notes,
            rag_citations,
            monitoring_guidance,
            clarifications,
            safety_level,
        )

    async def create_draft(self, user_id: str, req: PlanDraftRequest) -> PersonalizedPlanDTO:
        (
            goal,
            status,
            snap,
            habits,
            nutr,
            act,
            safety_notes,
            rag_citations,
            monitoring_guidance,
            clarifications,
            safety_level,
        ) = await self._build_plan_payload(
            user_id,
            goal_override=req.goal_override,
            user_note=req.user_note,
            reported_complaint=req.reported_complaint,
            nutrition_query=req.nutrition_query,
            city=req.city,
        )
        now = _utc_now()
        plan = PersonalizedPlan(
            id=f"plan-{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            version=1,
            parent_plan_id=None,
            status=status,
            goal=goal,
            profile_snapshot_json=json.dumps(snap, ensure_ascii=False),
            safety_level=safety_level,
            safety_notes_json=json.dumps(safety_notes, ensure_ascii=False),
            habits_json=json.dumps(habits, ensure_ascii=False),
            nutrition_section_json=json.dumps(nutr, ensure_ascii=False),
            activity_section_json=json.dumps(act, ensure_ascii=False),
            monitoring_guidance_json=json.dumps(monitoring_guidance, ensure_ascii=False),
            rag_citations_json=json.dumps(rag_citations, ensure_ascii=False),
            clarification_questions_json=json.dumps(clarifications, ensure_ascii=False),
            created_at=now,
            updated_at=now,
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return self._to_dto(plan)

    def list_plans(self, user_id: str) -> List[PersonalizedPlanDTO]:
        rows = (
            self.db.query(PersonalizedPlan)
            .filter(PersonalizedPlan.user_id == user_id)
            .order_by(PersonalizedPlan.created_at.desc(), PersonalizedPlan.version.desc())
            .all()
        )
        return [self._to_dto(r) for r in rows]

    def get_plan(self, user_id: str, plan_id: str) -> Optional[PersonalizedPlanDTO]:
        row = self.db.get(PersonalizedPlan, plan_id)
        if not row or row.user_id != user_id:
            return None
        return self._to_dto(row)

    def activate_plan(self, user_id: str, plan_id: str) -> Optional[PersonalizedPlanDTO]:
        row = self.db.get(PersonalizedPlan, plan_id)
        if not row or row.user_id != user_id:
            return None
        if row.safety_level == "urgent":
            raise ValueError("Rencana tidak dapat diaktifkan saat terdapat peringatan keselamatan mendesak.")
        self.db.query(PersonalizedPlan).filter(
            PersonalizedPlan.user_id == user_id,
            PersonalizedPlan.status == "active",
        ).update({"status": "archived"})
        row.status = "active" if row.safety_level == "none" else "needs_review"
        row.updated_at = _utc_now()
        self.db.commit()
        self.db.refresh(row)
        return self._to_dto(row)

    async def revise_plan(
        self, user_id: str, plan_id: str, req: PlanReviseRequest
    ) -> Optional[PersonalizedPlanDTO]:
        parent = self.db.get(PersonalizedPlan, plan_id)
        if not parent or parent.user_id != user_id:
            return None
        (
            goal,
            status,
            snap,
            habits,
            nutr,
            act,
            safety_notes,
            rag_citations,
            monitoring_guidance,
            clarifications,
            safety_level,
        ) = await self._build_plan_payload(
            user_id,
            goal_override=req.goal_override,
            user_note=req.user_note,
            reported_complaint=req.reported_complaint,
            nutrition_query=req.nutrition_query,
            city=req.city,
        )
        if parent.status == "active":
            parent.status = "archived"
        now = _utc_now()
        revised = PersonalizedPlan(
            id=f"plan-{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            version=parent.version + 1,
            parent_plan_id=parent.id,
            status=status,
            goal=goal,
            profile_snapshot_json=json.dumps(snap, ensure_ascii=False),
            safety_level=safety_level,
            safety_notes_json=json.dumps(safety_notes, ensure_ascii=False),
            habits_json=json.dumps(habits, ensure_ascii=False),
            nutrition_section_json=json.dumps(nutr, ensure_ascii=False),
            activity_section_json=json.dumps(act, ensure_ascii=False),
            monitoring_guidance_json=json.dumps(monitoring_guidance, ensure_ascii=False),
            rag_citations_json=json.dumps(rag_citations, ensure_ascii=False),
            clarification_questions_json=json.dumps(clarifications, ensure_ascii=False),
            revision_reason=req.revision_reason,
            created_at=now,
            updated_at=now,
        )
        self.db.add(revised)
        self.db.commit()
        self.db.refresh(revised)
        return self._to_dto(revised)

    def get_progress_summary(self, user_id: str) -> ProgressSummaryResponse:
        mon_rows = (
            self.db.query(MonitoringEntry)
            .filter(MonitoringEntry.user_id == user_id)
            .order_by(MonitoringEntry.recorded_at.desc())
            .limit(10)
            .all()
        )
        asm_rows = (
            self.db.query(Assessment)
            .filter(Assessment.user_id == user_id)
            .order_by(Assessment.created_at.desc())
            .limit(10)
            .all()
        )
        plan_rows = (
            self.db.query(PersonalizedPlan)
            .filter(PersonalizedPlan.user_id == user_id)
            .order_by(PersonalizedPlan.created_at.desc(), PersonalizedPlan.version.desc())
            .all()
        )
        active = next((p for p in plan_rows if p.status == "active"), None)
        latest_safety = "none"
        for a in asm_rows:
            if a.safety_level == "urgent":
                latest_safety = "urgent"
                break
            if a.safety_level == "review_recommended":
                latest_safety = "review_recommended"

        return ProgressSummaryResponse(
            monitoring_count=self.db.query(MonitoringEntry).filter(MonitoringEntry.user_id == user_id).count(),
            assessments_count=self.db.query(Assessment).filter(Assessment.user_id == user_id).count(),
            plans_count=len(plan_rows),
            active_plan_id=active.id if active else None,
            active_plan_version=active.version if active else None,
            latest_safety_level=latest_safety,
            recent_assessments=[
                {
                    "id": a.id,
                    "status": a.status,
                    "safety_level": a.safety_level,
                    "summary": a.summary,
                    "created_at": a.created_at.isoformat() + "Z",
                }
                for a in asm_rows[:5]
            ],
            recent_monitoring=[
                {
                    "id": m.id,
                    "wellbeing_note": m.wellbeing_note,
                    "recorded_at": m.recorded_at.isoformat() + "Z",
                }
                for m in mon_rows[:5]
            ],
            plan_history=[
                {
                    "id": p.id,
                    "version": p.version,
                    "parent_plan_id": p.parent_plan_id,
                    "status": p.status,
                    "goal": p.goal,
                    "revision_reason": p.revision_reason,
                    "updated_at": p.updated_at.isoformat() + "Z",
                }
                for p in plan_rows[:10]
            ],
        )

