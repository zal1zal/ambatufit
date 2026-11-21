"""
Seeds realistic synthetic demo data into AmbatuFit database.
Contains test users, health profiles, professionals, and appointment slots.
All data is strictly synthetic and complies with assignment rules.
"""
import sys
import os
from datetime import datetime, timedelta

# Ensure backend directory is in python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db import SessionLocal, init_db, User, HealthProfile, Professional, ProfessionalSlot
from app.security import hash_password


def seed_database():
    print("Initializing database tables...")
    init_db()
    db = SessionLocal()

    try:
        # Check if users already exist
        if db.query(User).filter(User.email == "pengguna.demo@ambatufit.local").first():
            print("Database already seeded. Skipping.")
            return

        print("Seeding demo accounts...")
        # 1. Demo User
        user = User(
            id="u-demo-001",
            email="pengguna.demo@ambatufit.local",
            password_hash=hash_password("DemoPass123!"),
            role="user",
            created_at=datetime.utcnow(),
        )
        db.add(user)

        # User profile
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

        # 2. Demo Professional 1 (Doctor)
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

        # 3. Demo Professional 2 (Dietitian)
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

        # 4. Schedule Slots for Next 3 Days
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        slot_counter = 1
        for day_offset in range(1, 4):
            day_base = now + timedelta(days=day_offset)
            # Slot 1: 09:00 - 10:00
            s1_start = day_base.replace(hour=9)
            s1_end = s1_start + timedelta(hours=1)
            db.add(ProfessionalSlot(
                id=f"slot-doc-{slot_counter}",
                professional_id="pro-doc-001",
                starts_at=s1_start,
                ends_at=s1_end,
                is_available=True,
            ))
            slot_counter += 1

            # Slot 2: 14:00 - 15:00
            s2_start = day_base.replace(hour=14)
            s2_end = s2_start + timedelta(hours=1)
            db.add(ProfessionalSlot(
                id=f"slot-diet-{slot_counter}",
                professional_id="pro-diet-001",
                starts_at=s2_start,
                ends_at=s2_end,
                is_available=True,
            ))
            slot_counter += 1

        db.commit()
        print("Demo database successfully seeded!")
        print("  User Account:         pengguna.demo@ambatufit.local / DemoPass123!")
        print("  Doctor Account:       dr.budi.santoso@ambatufit.local / DoctorPass123!")
        print("  Dietitian Account:    siti.aminah.sgz@ambatufit.local / DietitianPass123!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

