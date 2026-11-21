"""
Seeds synthetic demo users, health profile, professionals, and appointment slots.
All data is strictly synthetic. Medication catalogs are never fabricated in code;
they must be populated only from clinically reviewed files or verified migrations.
"""
import json
import os
import sys
from datetime import datetime, timedelta

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db import (
    SessionLocal,
    init_db,
    User,
    HealthProfile,
    Professional,
    ProfessionalSlot,
    MedicationCatalogItem,
)
from app.security import hash_password

DEMO_OTC_MEDICATIONS = [
    ("med-otc-loratadine", "Loratadine 10 mg", "Loratadine", "obat_bebas_terbatas", ["alergi ringan", "bersin", "hidung berair", "biduran"], ["Jarang menyebabkan kantuk, tetap berhati-hati saat berkendara bila terasa pusing."], ["Hipersensitivitas terhadap loratadine."], "https://pionas.pom.go.id/monografi/loratadin", "PIO Nas BPOM — Loratadine"),
    ("med-otc-ctm", "Chlorpheniramine Maleate (CTM) 4 mg", "Chlorpheniramine Maleate", "obat_bebas_terbatas", ["alergi ringan", "bersin", "gatal kulit", "pilek alergi"], ["Menyebabkan kantuk; jangan mengemudikan kendaraan atau mengoperasikan mesin."], ["Serangan asma akut, alergi CTM."], "https://pionas.pom.go.id/monografi/klorfeniramin-maleat", "PIO Nas BPOM — Klorfeniramin Maleat"),
    ("med-otc-bromhexine", "Bromhexine HCl 8 mg (Pengencer Dahak)", "Bromhexine Hydrochloride", "obat_bebas_terbatas", ["batuk berdahak", "dahak kental", "pilek batuk"], ["Minum air putih cukup untuk membantu mengencerkan dahak."], ["Riwayat tukak lambung aktif atau alergi bromhexine."], "https://pionas.pom.go.id/monografi/bromheksin", "PIO Nas BPOM — Bromheksin"),
    ("med-otc-simethicone", "Simethicone 80 mg (Tablet Kunyah)", "Simethicone", "obat_bebas", ["perut kembung", "penuh gas", "begah", "maag ringan"], ["Konsultasikan dokter bila nyeri perut hebat atau disertai demam."], ["Hipersensitivitas terhadap simethicone."], "https://medlineplus.gov/druginfo/meds/a682683.html", "MedlinePlus — Simethicone"),
    ("med-otc-bisacodyl", "Bisacodyl 5 mg (Tablet Salut Enterik)", "Bisacodyl", "obat_bebas_terbatas", ["sembelit", "konstipasi", "susah buang air besar"], ["Jangan dikunyah dan jangan diminum dalam 1 jam setelah susu atau antasida."], ["Nyeri perut hebat belum terdiagnosis, sumbatan usus."], "https://pionas.pom.go.id/monografi/bisakodil", "PIO Nas BPOM — Bisakodil"),
    ("med-otc-lactulose", "Laktulosa Sirup (Pencahar Osmotik)", "Lactulose", "obat_bebas", ["sembelit", "konstipasi", "tinja keras"], ["Perbanyak minum air putih saat menggunakan laktulosa."], ["Galaktosemia atau sumbatan saluran cerna."], "https://pionas.pom.go.id/monografi/laktulosa", "PIO Nas BPOM — Laktulosa"),
    ("med-otc-ferrous-folic", "Tablet Tambah Darah (Zat Besi + Asam Folat)", "Ferrous Sulfate & Folic Acid", "obat_bebas", ["kurang darah ringan", "anemia defisiensi besi", "lemas"], ["Tinja dapat berwarna gelap secara wajar; hindari diminum bersamaan dengan teh/kopi."], ["Hemokromatosis atau kelebihan zat besi."], "https://pionas.pom.go.id/monografi/fero-sulfat", "PIO Nas BPOM — Zat Besi"),
    ("med-otc-vitd3", "Vitamin D3 1000 IU", "Cholecalciferol (Vitamin D3)", "obat_bebas", ["suplemen kesehatan tulang", "daya tahan tubuh", "kurang paparan matahari"], ["Jangan melebihi dosis harian kemasan tanpa pemeriksaan kadar vitamin D."], ["Hiperkalsemia atau hipervitaminosis D."], "https://ods.od.nih.gov/factsheets/VitaminD-Consumer/", "NIH ODS — Vitamin D3"),
    ("med-otc-vitb-complex", "Vitamin B Kompleks", "Vitamin B1, B2, B3, B5, B6, B12", "obat_bebas", ["metabolisme energi", "pegal ringan", "pemulihan tubuh"], ["Urin dapat berwarna kuning cerah akibat vitamin B2 (wajar)."], ["Hipersensitivitas komponen vitamin B."], "https://medlineplus.gov/bvitamins.html", "MedlinePlus — Vitamin B Complex"),
    ("med-otc-povidone-gargle", "Povidone Iodine Obat Kumur 1%", "Povidone-Iodine", "obat_bebas_terbatas", ["sakit tenggorokan ringan", "bau mulut", "iritasi rongga mulut"], ["Hanya untuk berkumur di tenggorokan/mulut, JANGAN ditelan."], ["Alergi iodium atau gangguan tiroid tertentu."], "https://pionas.pom.go.id/monografi/povidon-iodum", "PIO Nas BPOM — Povidon Iodum"),
    ("med-otc-famotidine-10", "Famotidine 10 mg (Asam Lambung Ringan)", "Famotidine", "obat_bebas_terbatas", ["asam lambung naik", "heartburn", "maag ringan", "nyeri ulu hati"], ["Segera periksa ke dokter bila keluhan berlanjut lebih dari 14 hari."], ["Hipersensitivitas famotidine."], "https://medlineplus.gov/druginfo/meds/a687011.html", "MedlinePlus — Famotidine"),
    ("med-otc-loperamide-otc", "Loperamide HCl 2 mg (Diare Akut Non-Infeksi)", "Loperamide Hydrochloride", "obat_bebas_terbatas", ["diare akut tanpa demam", "bab cair non-infeksi"], ["Jangan digunakan bila diare disertai demam tinggi atau tinja berdarah."], ["Disentri akut dengan darah pada tinja atau demam tinggi."], "https://pionas.pom.go.id/monografi/loperamid", "PIO Nas BPOM — Loperamid"),
    ("med-otc-menthol-balm", "Balsem / Krim Menthol & Metil Salisilat", "Menthol & Methyl Salicylate", "obat_bebas", ["pegal otot", "nyeri punggung ringan", "keseleo ringan"], ["Hanya untuk pemakaian luar pada kulit utuh; jangan digunakan pada luka terbuka."], ["Kulit luka terbuka atau alergi salisilat."], "https://medlineplus.gov/druginfo/meds/a601129.html", "MedlinePlus — Topical Analgesics"),
    ("med-otc-hydrocortisone-cream", "Krim Hidrokortison 1% Topikal", "Hydrocortisone 1%", "obat_bebas_terbatas", ["gatal kulit ringan", "ruam kemerahan ringan", "gigitan serangga"], ["Oleskan tipis pada area gatal; jangan digunakan di wajah atau jangka panjang tanpa dokter."], ["Infeksi kulit akibat jamur/bakteri tanpa terapi khusus."], "https://medlineplus.gov/druginfo/meds/a682793.html", "MedlinePlus — Topical Hydrocortisone"),
]


def _upsert_extra_otc_medications(db):
    now = datetime.utcnow()
    added = 0
    for mid, name, ing, cat, ind, warn, contra, src_url, src_title in DEMO_OTC_MEDICATIONS:
        if db.query(MedicationCatalogItem).filter(MedicationCatalogItem.id == mid).first():
            continue
        db.add(
            MedicationCatalogItem(
                id=mid,
                display_name=name,
                active_ingredient=ing,
                category=cat,
                general_indications_json=json.dumps(ind, ensure_ascii=False),
                warnings_json=json.dumps(warn, ensure_ascii=False),
                contraindications_json=json.dumps(contra, ensure_ascii=False),
                source_reference_id=mid,
                source_title=src_title,
                source_url=src_url,
                verified_at=now,
                expires_at=now + timedelta(days=365),
                review_status="reviewed",
                review_version="1.1.0",
            )
        )
        added += 1
    if added:
        db.commit()
    print(f"OTC medication catalog check complete (+{added} added).")


def _ensure_demo_slots(db):
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    added = 0
    for day_offset in range(1, 5):
        day_base = now + timedelta(days=day_offset)
        for hour_idx, hour in enumerate((9, 14), 1):
            start_dt = day_base.replace(hour=hour)
            doc_id = f"slot-doc-d{day_offset}-{hour_idx}"
            if not db.query(ProfessionalSlot).filter(ProfessionalSlot.id == doc_id).first():
                db.add(
                    ProfessionalSlot(
                        id=doc_id,
                        professional_id="pro-doc-001",
                        starts_at=start_dt,
                        ends_at=start_dt + timedelta(hours=1),
                        is_available=True,
                    )
                )
                added += 1
            diet_id = f"slot-diet-d{day_offset}-{hour_idx}"
            if not db.query(ProfessionalSlot).filter(ProfessionalSlot.id == diet_id).first():
                db.add(
                    ProfessionalSlot(
                        id=diet_id,
                        professional_id="pro-diet-001",
                        starts_at=start_dt,
                        ends_at=start_dt + timedelta(hours=1),
                        is_available=True,
                    )
                )
                added += 1
    if added:
        db.commit()
    return added


def seed_database():
    print("Initializing database tables...")
    init_db()
    db = SessionLocal()

    try:
        _upsert_extra_otc_medications(db)
        if db.query(User).filter(User.email == "pengguna.demo@ambatufit.local").first():
            added_slots = _ensure_demo_slots(db)
            print(f"Database already seeded (+{added_slots} consultation slots ensured).")
            return

        print("Seeding synthetic demo accounts...")
        user = User(
            id="u-demo-001",
            email="pengguna.demo@ambatufit.local",
            password_hash=hash_password("DemoPass123!"),
            role="user",
            created_at=datetime.utcnow(),
        )
        db.add(user)

        profile = HealthProfile(
            user_id="u-demo-001",
            age_years=22,
            sex_for_model="unknown",
            health_goal="general_wellbeing",
            dietary_preferences_json='["balanced_meals"]',
            activity_preferences_json='["walking", "cycling"]',
            known_conditions_json='[]',
            updated_at=datetime.utcnow(),
        )
        db.add(profile)

        pro_doctor = User(
            id="pro-doc-001",
            email="dr.budi.santoso@ambatufit.local",
            password_hash=hash_password("DoctorPass123!"),
            role="professional",
            created_at=datetime.utcnow(),
        )
        db.add(pro_doctor)

        doc_profile = Professional(
            id="pro-doc-001",
            display_name="dr. Budi Santoso, Sp.KO (Spesialis Kedokteran Olahraga)",
            specialty="doctor",
            description="Dokter spesialis kedokteran olahraga dengan keahlian penanganan cedera fisik, pencegahan cedera, dan evaluasi keluhan muskuloskeletal pasca olahraga.",
            is_active=True,
        )
        db.add(doc_profile)

        pro_diet = User(
            id="pro-diet-001",
            email="siti.aminah.sgz@ambatufit.local",
            password_hash=hash_password("DietitianPass123!"),
            role="professional",
            created_at=datetime.utcnow(),
        )
        db.add(pro_diet)

        diet_profile = Professional(
            id="pro-diet-001",
            display_name="Siti Aminah, S.Gz, RD (Ahli Gizi Kebugaran)",
            specialty="dietitian",
            description="Ahli gizi teregistrasi dengan fokus pada perencanaan menu gizi seimbang, manajemen berat badan, dan asupan makronutrisi harian.",
            is_active=True,
        )
        db.add(diet_profile)

        db.commit()
        _ensure_demo_slots(db)
        print("Synthetic demo database successfully seeded!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
