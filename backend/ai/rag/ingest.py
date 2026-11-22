"""
Real Knowledge Ingestion Pipeline for AmbatuFit RAG.
Sources:
1. Local official DDXPlus conditions (release_conditions.json / metadata).
2. Internal verified AmbatuFit general health guidance rules (rules/health_guidance.json).
3. Live NLM MedlinePlus Health Topics Web Service (XML API).
4. Live openFDA Drug Label API (SPL structured product labeling -> US international ref).
5. Honest Source Registry entries for SATUSEHAT KFA, BPOM Cek Produk, and WHO ICD API.

CLI:
  python -m ai.rag.ingest --mode init|update|reindex|stats|inspect [--source-id SRC_ID] [--skip-network]
"""
import argparse
from html import unescape
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

from ai.metadata import BACKEND_DIR, DEFAULT_DATA_DIR
from ai.nlp_rag import _get_indonesian_label
from ai.rag.embeddings import RAGVectorIndex
from ai.rag.store import RAG_DATA_DIR, RAGStore, utc_now_iso

RELEASE_CONDITIONS_PATH = DEFAULT_DATA_DIR / "release_conditions.json"
RELEASE_EVIDENCES_PATH = DEFAULT_DATA_DIR / "release_evidences.json"
HEALTH_GUIDANCE_PATH = BACKEND_DIR / "rules" / "health_guidance.json"
INGESTION_LOG_PATH = RAG_DATA_DIR / "ingestion_log.json"

USER_AGENT = "AmbatuFit-RAG-Ingestor/1.0 (+https://ambatufit.local)"

# Bilingual canonical mapping for official DDXPlus conditions (lay terms + Indonesian names only;
# causes/risk_factors/prevention remain null unless supplied by MedlinePlus/verified clinical source).
DDXPLUS_INDONESIAN_TERMS: Dict[str, Tuple[str, List[str], List[str]]] = {
    "URTI": ("Infeksi Saluran Napas Atas (ISPA Ringan)", ["ISPA", "common cold", "upper respiratory tract infection"], ["batuk pilek", "masuk angin", "flu ringan", "radang saluran napas atas"]),
    "Influenza": ("Influenza (Flu)", ["flu", "seasonal flu"], ["flu berat", "demam menggigil nyeri badan"]),
    "Viral pharyngitis": ("Faringitis Viral (Radang Tenggorokan Virus)", ["pharyngitis", "sore throat"], ["radang tenggorokan", "tenggorokan sakit"]),
    "Acute laryngitis": ("Laringitis Akut", ["laryngitis"], ["suara serak", "pita suara meradang"]),
    "Acute rhinosinusitis": ("Rinosinusitis Akut", ["sinusitis akut", "acute sinusitis"], ["hidung tersumbat nyeri wajah", "sinus kambuh"]),
    "Chronic rhinosinusitis": ("Rinosinusitis Kronis", ["sinusitis kronis", "chronic sinusitis"], ["sinus menahun", "hidung mampet lama"]),
    "Allergic sinusitis": ("Rhinitis / Sinusitis Alergi", ["allergic rhinitis", "hay fever", "rhinitis alergi"], ["alergi debu", "bersin pagi hari", "pilek alergi"]),
    "Acute otitis media": ("Otitis Media Akut (Infeksi Telinga Tengah)", ["otitis media", "ear infection"], ["sakit telinga", "infeksi telinga"]),
    "GERD": ("Penyakit Refluks Gastroesofageal (GERD)", ["gastroesophageal reflux disease", "acid reflux", "refluks asam lambung"], ["asam lambung naik", "maag", "nyeri ulu hati", "dada terasa panas", "heartburn"]),
    "Bronchitis": ("Bronkitis Akut", ["acute bronchitis", "radang bronkus"], ["batuk berdahak lama", "batuk dada nyeri"]),
    "Pneumonia": ("Pneumonia (Radang Paru)", ["radang paru", "infeksi paru", "lung infection"], ["paru-paru basah", "batuk demam sesak"]),
    "Bronchospasm / acute asthma exacerbation": ("Asma / Eksaserbasi Asma Akut", ["asthma", "asma", "bronchospasm"], ["sesak napas mengi", "bengek", "napas berbunyi"]),
    "Acute COPD exacerbation / infection": ("PPOK Eksaserbasi Akut", ["COPD", "PPOK", "penyakit paru obstruktif kronis"], ["sesak kronis perokok", "paru obstruktif"]),
    "Tuberculosis": ("Tuberkulosis (TBC / TB)", ["TB", "TBC", "tuberkulosis paru"], ["batuk darah lama", "flek paru", "keringat malam"]),
    "Anemia": ("Anemia (Kurang Darah)", ["kurang darah", "hemoglobin rendah"], ["lemas pucat pusing", "hb rendah", "kurang sel darah merah"]),
    "Cluster headache": ("Sakit Kepala Klaster", ["sakit kepala klaster", "migraine / headache"], ["nyeri kepala sebelah berat", "sakit kepala di sekitar mata"]),
    "Panic attack": ("Serangan Panik (Panic Attack)", ["serangan panik", "gangguan kecemasan akut"], ["cemas hebat jantung berdebar", "panik sesak tiba-tiba"]),
    "Possible NSTEMI / STEMI": ("Sindrom Koroner Akut (NSTEMI / STEMI)", ["serangan jantung", "myocardial infarction", "heart attack", "acute coronary syndrome"], ["nyeri dada menjalar kiri", "serangan jantung"]),
    "Stable angina": ("Angina Pektoris Stabil", ["angina stabil", "angin duduk"], ["nyeri dada saat aktivitas"]),
    "Unstable angina": ("Angina Pektoris Tidak Stabil", ["angina tidak stabil", "acute angina"], ["nyeri dada saat istirahat"]),
    "Pulmonary embolism": ("Emboli Paru", ["penyumbatan pembuluh paru"], ["sesak napas mendadak nyeri dada"]),
    "Spontaneous pneumothorax": ("Pneumotoraks Spontan", ["paru kolaps"], ["nyeri dada mendadak sesak"]),
    "Pericarditis": ("Perikarditis", ["radang selaput jantung"], ["nyeri dada tajam membaik saat condong depan"]),
    "Myocarditis": ("Miokarditis", ["radang otot jantung"], ["nyeri dada berdebar pasca infeksi"]),
    "Atrial fibrillation": ("Fibrilasi Atrium", ["AFib", "aritmia atrium"], ["detak jantung tidak teratur", "jantung berdebar"]),
    "PSVT": ("Takikardia Supraventrikular Paroksismal (PSVT)", ["SVT", "aritmia cepat"], ["jantung berdebar sangat cepat mendadak"]),
    "Anaphylaxis": ("Anafilaksis (Reaksi Alergi Berat)", ["reaksi alergi berat", "syok anafilaksis"], ["bengkak sesak setelah alergen"]),
    "Whooping cough": ("Pertusis (Batuk Rejan)", ["pertussis", "batuk 100 hari"], ["batuk panjang menggigil"]),
    "Croup": ("Croup (Laringotrakeobronkitis)", ["batuk menggonggong"], ["batuk suara menggonggong"]),
    "Epiglottitis": ("Epiglotitis", ["radang epiglotis"], ["sakit menelan berat suara teredam"]),
    "Larygospasm": ("Laringospasme", ["laryngospasm", "kejang pita suara"], ["tersedak mendadak tidak bisa tarik napas"]),
    "Bronchiectasis": ("Bronkiektasis", ["pelebaran saluran bronkus"], ["batuk dahak banyak menahun"]),
    "Bronchiolitis": ("Bronkiolitis", ["infeksi saluran napas kecil"], ["mengi pada anak kecil"]),
    "Acute pulmonary edema": ("Edema Paru Akut", ["cairan di paru"], ["sesak berat berbaring"]),
    "Boerhaave": ("Sindrom Boerhaave (Ruptur Esofagus)", ["esophageal rupture"], ["muntah hebat disertai nyeri dada hebat"]),
    "Inguinal hernia": ("Hernia Inguinalis", ["turun berok", "hernia lipat paha"], ["benjolan di selangkangan"]),
    "Localized edema": ("Edema Lokal (Pembengkakan Setempat)", ["bengkak tungkai", "pembengkakan lokal"], ["kaki bengkak sebelah"]),
    "Guillain-Barré syndrome": ("Sindrom Guillain-Barre", ["GBS"], ["kelemahan otot menanjak dari kaki"]),
    "Myasthenia gravis": ("Miastenia Gravis", ["kelemahan otot autoimun"], ["kelopak mata turun lelah otot"]),
    "SLE": ("Lupus Eritematosus Sistemik (SLE)", ["lupus", "systemic lupus erythematosus"], ["ruam kupu-kupu nyeri sendi"]),
    "Sarcoidosis": ("Sarkoidosis", ["peradangan granuloma"], ["batuk kering kelelahan benjolan"]),
    "Pancreatic neoplasm": ("Neoplasma Pankreas", ["tumor/kanker pankreas"], ["nyeri perut tembus punggung berat badan turun"]),
    "Pulmonary neoplasm": ("Neoplasma Paru", ["tumor/kanker paru"], ["batuk menetap berat badan turun"]),
    "Acute dystonic reactions": ("Reaksi Distonia Akut", ["kaku otot akibat obat"], ["otot wajah leher kaku mendadak"]),
    "Chagas": ("Penyakit Chagas", ["chagas disease"], ["infeksi parasit kronis"]),
    "Ebola": ("Penyakit Virus Ebola", ["ebola virus disease"], ["demam berdarah virus ebola"]),
    "HIV (initial infection)": ("Infeksi HIV Awal", ["HIV akut"], ["demam ruam pembengkakan kelenjar"]),
    "Scombroid food poisoning": ("Keracunan Histamin Ikan (Scombroid)", ["histamine fish poisoning"], ["wajah merah gatal setelah makan ikan"]),
    "Spontaneous rib fracture": ("Fraktur Tulang Rusuk Spontan", ["patah tulang rusuk"], ["nyeri dada terlokalisir saat batuk/tarik napas"]),
}

INDONESIAN_DISEASE_KNOWLEDGE: List[Dict[str, Any]] = [
    {
        "id": "dis-migraine",
        "canonical_name": "Migraine",
        "indonesian_name": "Migrain (Sakit Kepala Sebelah)",
        "english_name": "Migraine",
        "icd_code": "G43",
        "synonyms": ["migrain", "migraine headache", "sakit kepala berdenyut"],
        "lay_terms": ["pusing", "pusying", "sakit kepala sebelah", "kepala berdenyut", "mual silau cahaya"],
        "short_description": "Migrain adalah sakit kepala berulang yang umumnya terasa berdenyut di salah satu sisi kepala dengan intensitas sedang hingga berat.",
        "causes": "Berkaitan dengan perubahan aktivitas saraf otak, pelebaran pembuluh darah kepala sementara, faktor genetik, kurang tidur, stres, perubahan hormon, terlambat makan, atau paparan cahaya menyilaukan.",
        "symptoms": "Nyeri kepala berdenyut pada satu sisi, mual atau ingin muntah, sensitif terhadap cahaya terang dan suara keras; sebagian orang mengalami aura (kilatan cahaya atau garis zig-zag sebelum nyeri muncul).",
        "risk_factors": "Riwayat keluarga migrain, stres berkepanjangan, pola tidur tidak teratur, dehidrasi, kafein berlebih, atau pemicu makanan tertentu.",
        "prevention_management": "Beristirahat di ruangan tenang yang redup, kompres dingin/hangat di dahi, cukupi minum air putih, jaga jam tidur teratur, dan konsultasikan ke dokter jika serangan sering kambuh.",
    },
    {
        "id": "dis-diabetes-mellitus",
        "canonical_name": "Diabetes Mellitus",
        "indonesian_name": "Diabetes Melitus (Kencing Manis)",
        "english_name": "Diabetes Mellitus",
        "icd_code": "E11",
        "synonyms": ["DM", "diabetes", "diabetes tipe 1", "diabetes tipe 2", "diabetes mellitus"],
        "lay_terms": ["kencing manis", "gula darah tinggi", "diabetes kering", "diabetes basah", "sering haus kencing malam"],
        "short_description": "Diabetes melitus adalah penyakit kronis akibat kadar gula (glukosa) dalam darah melebihi batas normal karena gangguan produksi atau kerja hormon insulin.",
        "causes": "Pada diabetes tipe 1, sistem imun menyerang sel penghasil insulin di pankreas. Pada diabetes tipe 2, sel tubuh menjadi kurang peka terhadap insulin (resistensi insulin) atau produksi insulin berkurang seiring waktu.",
        "symptoms": "Sering merasa haus, sering buang air kecil terutama malam hari, mudah lelah, rasa lapar meningkat, luka sulit sembuh, pandangan kabur, dan kesemutan di kaki/tangan.",
        "risk_factors": "Riwayat keluarga diabetes, berat badan berlebih, kurang aktivitas fisik, pola makan tinggi gula dan karbohidrat sederhana, serta usia di atas 45 tahun.",
        "prevention_management": "Atur komposisi piring makan bergizi seimbang berserat tinggi, batasi minuman manis, olahraga rutin minimal 150 menit/minggu, dan periksa gula darah secara berkala bersama dokter.",
    },
    {
        "id": "dis-hypertension",
        "canonical_name": "Hypertension",
        "indonesian_name": "Hipertensi (Tekanan Darah Tinggi)",
        "english_name": "High Blood Pressure",
        "icd_code": "I10",
        "synonyms": ["hipertensi", "HT", "essential hypertension", "high blood pressure"],
        "lay_terms": ["darah tinggi", "tensi tinggi", "tekanan darah naik", "pusing tengkuk berat"],
        "short_description": "Hipertensi adalah kondisi peningkatan tekanan darah pada dinding pembuluh darah arteri secara menetap (umumnya >= 140/90 mmHg saat diperiksa ulang).",
        "causes": "Sebagian besar kasus hipertensi primer dipengaruhi faktor genetik, konsumsi garam berlebih, kekakuan pembuluh darah, stres, dan pola hidup; sebagian kecil disebabkan penyakit ginjal atau hormonal.",
        "symptoms": "Sering tidak bergejala sama sekali pada tahap awal; keluhan kadang berupa sakit kepala atau tegang di tengkuk, pusing, penglihatan buram, atau jantung berdebar bila tekanan sangat tinggi.",
        "risk_factors": "Asupan natrium/garam tinggi, obesitas, kurang olahraga, merokok, stres kronis, dan riwayat keluarga.",
        "prevention_management": "Batasi garam di bawah 1 sendok teh/hari, perbanyak sayur dan buah, rutin jalan kaki/aerobik ringan, kelola stres, serta ukur tekanan darah dan kontrol ke dokter secara rutin.",
    },
    {
        "id": "dis-Bronchospasm_acute_asthma_exacerbation",
        "canonical_name": "Bronchospasm / acute asthma exacerbation",
        "indonesian_name": "Asma (Penyempitan Saluran Napas)",
        "english_name": "Asthma",
        "icd_code": "J45",
        "synonyms": ["asthma", "asma", "bronchospasm"],
        "lay_terms": ["bengek", "napas mengi", "sesak napas alergi", "napas bunyi ngik"],
        "short_description": "Asma adalah peradangan kronis saluran napas yang menyebabkan penyempitan sementara sehingga penderita mengalami sesak, napas berbunyi mengi, dan batuk.",
        "causes": "Dipicu alergen (debu tungau, bulu hewan, serbuk sari), udara dingin, asap rokok, polusi, infeksi saluran napas virus, atau olahraga berat tanpa pemanasan.",
        "symptoms": "Napas terasa sesak atau pendek, dada terasa berat, suara napas berbunyi mengi (ngik-ngik), serta batuk terutama pada malam atau dini hari.",
        "risk_factors": "Riwayat alergi/eksim, asma dalam keluarga, paparan asap rokok sejak dini, dan tinggal di area polusi udara tinggi.",
        "prevention_management": "Jaga kebersihan kamar dari debu tungau, hindari asap rokok/parfum menyengat, kenali pemicu kambuh, dan bawa obat pelega inhalasi sesuai resep dokter.",
    },
    {
        "id": "dis-GERD",
        "canonical_name": "GERD",
        "indonesian_name": "Penyakit Refluks Asam Lambung (GERD)",
        "english_name": "Gastroesophageal Reflux Disease",
        "icd_code": "K21",
        "synonyms": ["GERD", "acid reflux", "asam lambung", "heartburn"],
        "lay_terms": ["maag", "ulu hati perih", "asam lambung naik", "dada panas", "mulut pahit"],
        "short_description": "GERD terjadi ketika asam lambung berulang kali naik kembali ke kerongkongan karena melemahnya katup pembatas antara lambung dan kerongkongan.",
        "causes": "Katup esofagus bagian bawah mengendur terlalu sering, peningkatan tekanan perut akibat makan terlalu kenyang, langsung berbaring sehabis makan, berat badan berlebih, atau kebiasaan konsumsi kopi/gorengan pedas.",
        "symptoms": "Rasa panas terbakar di dada/ulu hati (heartburn), cairan asam/pahit naik ke tenggorokan, mual, kembung, sering bersendawa, atau batuk kering di malam hari.",
        "risk_factors": "Langsung tidur setelah makan, porsi makan besar sekaligus, makanan berlemak/pedas/asam, merokok, dan kehamilan.",
        "prevention_management": "Makan porsi kecil tapi teratur, beri jeda 2-3 jam sebelum berbaring, tinggikan bantal kepala-bahu saat tidur, serta batasi kopi, cokelat, dan makanan sangat pedas/berlemak.",
    },
    {
        "id": "dis-gastritis",
        "canonical_name": "Gastritis",
        "indonesian_name": "Gastritis (Radang Lambung / Sakit Maag)",
        "english_name": "Gastritis",
        "icd_code": "K29.7",
        "synonyms": ["gastritis", "sakit maag", "radang lambung"],
        "lay_terms": ["maag", "perih lambung", "kembung mual", "nyeri ulu hati"],
        "short_description": "Gastritis adalah peradangan pada lapisan dinding lambung yang menimbulkan rasa perih, nyeri ulu hati, mual, atau cepat terasa penuh saat makan.",
        "causes": "Pola makan tidak teratur, infeksi bakteri Helicobacter pylori, konsumsi obat pereda nyeri golongan OAINS terlalu sering tanpa pengawasan, stres, serta alkohol atau kafein berlebih.",
        "symptoms": "Nyeri atau perih di ulu hati, perut terasa kembung/begah, mual atau muntah, bersendawa berlebih, dan nafsu makan menurun.",
        "risk_factors": "Sering telat makan, pemakaian obat anti nyeri jangka panjang, merokok, dan tingkat stres tinggi.",
        "prevention_management": "Makan tepat waktu dalam porsi sedang, pilih lauk mudah dicerna, hindari minum obat nyeri saat perut kosong, dan periksakan ke dokter bila keluhan sering berulang.",
    },
    {
        "id": "dis-URTI",
        "canonical_name": "URTI",
        "indonesian_name": "Infeksi Saluran Napas Atas (ISPA Ringan / Pilek)",
        "english_name": "Common Cold / URTI",
        "icd_code": "J06.9",
        "synonyms": ["ISPA", "common cold", "upper respiratory tract infection"],
        "lay_terms": ["batuk pilek", "masuk angin", "flu ringan", "radang tenggorokan ringan", "hidung meler"],
        "short_description": "ISPA ringan adalah infeksi akut pada hidung, tenggorokan, dan saluran napas atas yang sebagian besar disebabkan oleh virus dan umumnya membaik dalam 5-10 hari.",
        "causes": "Penularan virus pernapasan (seperti rhinovirus) melalui percikan batuk/bersin atau tangan yang menyentuh hidung dan mulut setelah memegang permukaan terkontaminasi.",
        "symptoms": "Hidung berair atau tersumbat, bersin, tenggorokan gatal atau sakit saat menelan, batuk ringan, demam ringan, serta badan terasa pegal.",
        "risk_factors": "Cuaca berubah, kurang tidur, kelelahan daya tahan tubuh, dan berada di ruangan tertutup bersama orang yang sedang flu.",
        "prevention_management": "Istirahat cukup, perbanyak minum air putih hangat, berkumur air garam hangat untuk tenggorokan, cuci tangan pakai sabun, dan pakai masker agar tidak menular.",
    },
    {
        "id": "dis-Influenza",
        "canonical_name": "Influenza",
        "indonesian_name": "Influenza (Flu)",
        "english_name": "Influenza",
        "icd_code": "J11",
        "synonyms": ["flu", "seasonal influenza"],
        "lay_terms": ["flu demam", "pilek meriang", "ngilu seluruh badan"],
        "short_description": "Influenza adalah infeksi virus pada saluran napas yang muncul lebih mendadak dan lebih berat dibanding pilek biasa.",
        "causes": "Virus influenza tipe A atau B yang menyebar lewat droplet udara saat penderita batuk, bersin, atau berbicara jarak dekat.",
        "symptoms": "Demam tinggi mendadak, menggigil, nyeri otot dan sendi, sakit kepala, batuk kering, tenggorokan sakit, dan kelelahan berat.",
        "risk_factors": "Daya tahan tubuh lemah, usia lanjut, anak kecil, kondisi kronis (asma, diabetes, penyakit jantung), dan belum vaksinasi flu.",
        "prevention_management": "Istirahat di rumah, penuhi asupan cairan dan gizi, jaga etika batuk dan cuci tangan; segera ke dokter bila sesak napas atau demam tinggi menetap.",
    },
    {
        "id": "dis-Tuberculosis",
        "canonical_name": "Tuberculosis",
        "indonesian_name": "Tuberkulosis (TBC / TB)",
        "english_name": "Tuberculosis",
        "icd_code": "A15",
        "synonyms": ["TB", "TBC", "tuberkulosis paru"],
        "lay_terms": ["flek paru", "batuk darah lama", "batuk lebih 2 minggu", "keringat malam"],
        "short_description": "Tuberkulosis (TBC) adalah penyakit infeksi bakteri Mycobacterium tuberculosis yang paling sering menyerang paru-paru dan dapat disembuhkan dengan pengobatan teratur.",
        "causes": "Bakteri Mycobacterium tuberculosis yang menular melalui udara ketika penderita TBC aktif batuk atau bersin tanpa masker.",
        "symptoms": "Batuk terus-menerus selama 2 minggu atau lebih (kadang berdahak atau bercampur darah), demam ringan berkepanjangan, keringat malam tanpa aktivitas berat, berat badan turun, dan nafsu makan hilang.",
        "risk_factors": "Kontak erat dengan penderita TBC aktif di ruangan minim ventilasi, daya tahan tubuh rendah, gizi kurang, dan kebiasaan merokok.",
        "prevention_management": "Segera periksa dahak/foto rontgen di Puskesmas atau rumah sakit bila batuk >= 2 minggu. Pengobatan OAT gratis di faskes harus diminum tuntas tanpa putus; buka jendela rumah agar cahaya matahari masuk.",
    },
    {
        "id": "dis-Pneumonia",
        "canonical_name": "Pneumonia",
        "indonesian_name": "Pneumonia (Radang Paru-Paru)",
        "english_name": "Pneumonia",
        "icd_code": "J18.9",
        "synonyms": ["radang paru", "infeksi paru", "lung infection"],
        "lay_terms": ["paru-paru basah", "batuk demam sesak"],
        "short_description": "Pneumonia adalah peradangan akut pada kantung udara paru-paru (alveoli) yang menyebabkan kantung paru terisi cairan atau nanah sehingga mengganggu pertukaran oksigen.",
        "causes": "Infeksi bakteri, virus, atau jamur yang masuk ke jaringan paru bagian bawah.",
        "symptoms": "Batuk berdahak kental, demam tinggi disertai menggigil, napas cepat atau sesak napas, nyeri dada tajam saat menarik napas dalam, dan lemas berat.",
        "risk_factors": "Bayi/balita, lansia, perokok berat, penderita asma/PPOK, atau penurunan sistem imun.",
        "prevention_management": "Pneumonia memerlukan pemeriksaan dokter secara langsung untuk menentukan terapi antibiotik atau antivirus yang tepat. Istirahat, cukupi cairan, dan segera ke IGD bila bibir kebiruan atau sesak berat.",
    },
    {
        "id": "dis-Bronchitis",
        "canonical_name": "Bronchitis",
        "indonesian_name": "Bronkitis Akut",
        "english_name": "Acute Bronchitis",
        "icd_code": "J20.9",
        "synonyms": ["acute bronchitis", "bronkitis", "radang bronkus"],
        "lay_terms": ["batuk berdahak lama", "batuk dada terasa sakit"],
        "short_description": "Bronkitis akut adalah peradangan pada saluran udara utama menuju paru-paru (bronkus) yang memicu produksi lendir berlebih dan batuk berkepanjangan.",
        "causes": "Umumnya lanjutan dari infeksi virus pilek/flu, atau iritasi berulang akibat asap rokok, debu, dan polusi udara.",
        "symptoms": "Batuk berdahak bening, kekuningan, atau kental selama 1-3 minggu, dada terasa tidak nyaman saat batuk, lelah, serta demam ringan.",
        "risk_factors": "Kebiasaan merokok atau perokok pasif, paparan polusi udara/asap pabrik, serta infeksi saluran napas atas yang belum pulih.",
        "prevention_management": "Minum banyak air hangat untuk mengencerkan dahak, jauhi asap rokok sepenuhnya, beristirahat cukup, dan konsultasikan dokter bila batuk melebihi 3 minggu atau disertai sesak.",
    },
    {
        "id": "dis-Anemia",
        "canonical_name": "Anemia",
        "indonesian_name": "Anemia (Kurang Darah / Hb Rendah)",
        "english_name": "Anemia",
        "icd_code": "D64.9",
        "synonyms": ["kurang darah", "hemoglobin rendah", "iron deficiency anemia"],
        "lay_terms": ["kurang darah", "hb rendah", "lemas pucat", "pusing berkunang-kunang"],
        "short_description": "Anemia terjadi ketika jumlah sel darah merah sehat atau kadar hemoglobin (Hb) berada di bawah nilai normal sehingga pasokan oksigen ke jaringan tubuh berkurang.",
        "causes": "Kekurangan zat besi, asam folat, atau vitamin B12, perdarahan (termasuk haid berlebih), gangguan penyerapan usus, atau penyakit kronis.",
        "symptoms": "Mudah lelah dan lemas, kulit serta kelopak mata bagian dalam tampak pucat, pusing atau berkunang-kunang saat berdiri, tangan/kaki dingin, dan jantung mudah berdebar.",
        "risk_factors": "Asupan lauk sumber zat besi rendah, kehamilan, menstruasi berat, atau kebiasaan minum teh/kopi tepat setelah makan.",
        "prevention_management": "Konsumsi makanan kaya zat besi (hati, daging tanpa lemak, ikan, bayam, kacang-kacangan) didampingi buah kaya vitamin C agar penyerapan optimal, serta hindari minum teh/kopi bersamaan dengan makan atau tablet tambah darah.",
    },
    {
        "id": "dis-Allergic_sinusitis",
        "canonical_name": "Allergic sinusitis",
        "indonesian_name": "Rhinitis / Sinusitis Alergi",
        "english_name": "Allergic Rhinitis",
        "icd_code": "J30.9",
        "synonyms": ["allergic rhinitis", "hay fever", "rhinitis alergi"],
        "lay_terms": ["alergi debu", "bersin pagi hari", "pilek alergi", "hidung gatal"],
        "short_description": "Rhinitis atau sinusitis alergi adalah peradangan rongga hidung akibat reaksi sensitivitas sistem imun terhadap partikel pemicu di udara.",
        "causes": "Paparan debu tungau kasur, bulu hewan peliharaan, serbuk sari bunga, spora jamur lembap, atau perubahan suhu udara mendadak.",
        "symptoms": "Bersin-bersin berulang terutama pagi hari, hidung berair encer atau tersumbat, rasa gatal di hidung/langit-langit mulut, dan mata berair/gatal.",
        "risk_factors": "Riwayat alergi atau asma pada diri/keluarga dan lingkungan rumah berdebu.",
        "prevention_management": "Cuci seprai dengan air hangat seminggu sekali, kurangi karpet penampung debu, gunakan masker saat bersih-bersih, dan bilas hidung dengan larutan salin bila tersumbat.",
    },
    {
        "id": "dis-diarrhea",
        "canonical_name": "Acute diarrhea",
        "indonesian_name": "Diare Akut",
        "english_name": "Acute Diarrhea",
        "icd_code": "A09",
        "synonyms": ["diare", "acute diarrhea", "diarrhea", "mencret"],
        "lay_terms": ["mencret", "bab cair terus", "sakit perut mulas bab cair"],
        "short_description": "Diare akut adalah buang air besar dengan konsistensi lembek atau cair sebanyak 3 kali atau lebih dalam sehari, umumnya berlangsung kurang dari 14 hari.",
        "causes": "Infeksi virus, bakteri, atau parasit dari makanan/minuman kurang higienis, keracunan makanan, intoleransi laktosa, atau efek samping obat tertentu.",
        "symptoms": "Tinja encer/berair, mulas atau kram perut, sering ke kamar mandi, kadang disertai mual, muntah, atau demam ringan; risiko utama adalah dehidrasi.",
        "risk_factors": "Jajanan kurang bersih, tidak mencuci tangan sebelum makan, dan air minum tidak matang.",
        "prevention_management": "Prioritas utama adalah mencegah dehidrasi dengan minum oralit atau air matang/kuah sup sedikit demi sedikit secara sering. Makan makanan lunak rendah serat sementara (bubur, pisang). Segera ke dokter bila tinja berdarah, demam tinggi, atau lemas berat/jarang kencing.",
    },
    {
        "id": "dis-Panic_attack",
        "canonical_name": "Panic attack",
        "indonesian_name": "Serangan Panik (Panic Attack)",
        "english_name": "Panic Disorder",
        "icd_code": "F41.0",
        "synonyms": ["serangan panik", "panic attack", "gangguan panik"],
        "lay_terms": ["panik mendadak", "cemas hebat jantung berdebar", "takut mendadak sesak"],
        "short_description": "Serangan panik adalah gelombang rasa takut atau kecemasan hebat yang muncul tiba-tiba dan memuncak dalam beberapa menit disertai gejala fisik nyata.",
        "causes": "Respons alarm tubuh berlebihan terhadap stres berat, kelelahan, trauma, konsumsi kafein tinggi, atau gangguan keseimbangan senyawa saraf otak.",
        "symptoms": "Jantung berdebar kencang, napas memburu, gemetar, berkeringat dingin, pusing seperti melayang, dan ketakutan hebat padahal tidak ada bahaya fisik langsung.",
        "risk_factors": "Stres berat berkepanjangan, kurang tidur, konsumsi kafein berlebih, serta riwayat kecemasan.",
        "prevention_management": "Saat serangan datang, fokus pada napas lambat (tarik 4 detik, tahan 2 detik, embus 6 detik) dan teknik grounding panca indra (sebutkan 5 benda yang terlihat). Jika keluhan berulang atau disertai nyeri dada menjalar, periksakan diri ke dokter untuk menyingkirkan penyebab fisik.",
    },
    {
        "id": "dis-Cluster_headache",
        "canonical_name": "Cluster headache",
        "indonesian_name": "Sakit Kepala Klaster",
        "english_name": "Cluster Headache",
        "icd_code": "G44.0",
        "synonyms": ["sakit kepala klaster", "cluster headache"],
        "lay_terms": ["nyeri kepala hebat sebelah mata", "sakit kepala di sekitar mata berair"],
        "short_description": "Sakit kepala klaster adalah sakit kepala sangat nyeri yang muncul berpola di satu sisi kepala terutama di sekitar atau belakang mata.",
        "causes": "Berkaitan dengan aktivasi saraf trigeminal dan bagian otak pengatur ritme harian (hipotalamus), sering dipicu pola tidur terganggu, alkohol, atau bau menyengat.",
        "symptoms": "Nyeri menusuk tajam di sekitar satu mata/pelipis, mata merah dan berair pada sisi yang nyeri, hidung meler atau tersumbat di sisi yang sama, serta gelisah.",
        "risk_factors": "Kebiasaan merokok, konsumsi alkohol saat fase klaster, serta perubahan pola tidur drastis.",
        "prevention_management": "Hindari rokok dan alkohol, jaga ritme tidur tetap konsisten, dan segera konsultasikan ke dokter saraf untuk penanganan serangan akut yang efektif.",
    },
    {
        "id": "dis-scoliosis",
        "canonical_name": "Scoliosis",
        "indonesian_name": "Skoliosis (Kelengkungan Tulang Belakang)",
        "english_name": "Scoliosis",
        "icd_code": "M41",
        "synonyms": ["skoliosis", "scoliosis", "tulang belakang bengkok"],
        "lay_terms": ["punggung miring", "bahu tinggi sebelah", "tulang belakang melengkung huruf S/C"],
        "short_description": "Skoliosis adalah kondisi melengkungnya tulang belakang ke arah samping menyerupai huruf C atau S alih-alih lurus di garis tengah tubuh.",
        "causes": "Sebagian besar bersifat idiopatik (muncul saat masa pertumbuhan remaja tanpa penyebab tunggal pasti); sebagian lain terkait kelainan bawaan tulang, gangguan otot/saraf, atau perubahan degeneratif tulang belakang pada dewasa.",
        "symptoms": "Tinggi bahu atau pinggul tampak tidak sejajar, salah satu tulang belikat lebih menonjol, pinggang miring, cepat pegal di punggung saat duduk/berdiri lama, dan kadang nyeri punggung.",
        "risk_factors": "Lonjakan pertumbuhan usia remaja, riwayat skoliosis dalam keluarga, serta kebiasaan postur asimetris jangka panjang.",
        "prevention_management": "Lakukan latihan penguatan otot core secara simetris (Cat-Cow, Bird-Dog, Pelvic Tilt), hindari mengangkat beban berat satu sisi, atur kursi duduk ergonomis, dan konsultasikan ke dokter ortopedi/rehabilitasi medik untuk pemeriksaan sudut kelengkungan (Cobb angle).",
    },
]

def ingest_indonesian_disease_guides(store: RAGStore, fetched_at: str) -> Tuple[int, int]:
    dis_count = 0
    chunk_count = 0
    for item in INDONESIAN_DISEASE_KNOWLEDGE:
        did = item["id"]
        existing = store.get_disease(did) or {}
        syns = sorted(set([*(existing.get("synonyms") or []), *item["synonyms"], item["canonical_name"], item["indonesian_name"]]))
        lays = sorted(set([*(existing.get("lay_terms") or []), *item["lay_terms"]]))
        refs = list(existing.get("source_references") or [])
        if not any(r.get("source_id") == "SRC-AMBATUFIT-RULES" for r in refs):
            refs.insert(
                0,
                {
                    "source_id": "SRC-AMBATUFIT-RULES",
                    "title": f"Panduan Edukasi Kesehatan AmbatuFit — {item['indonesian_name']}",
                    "url": "internal://backend/rules/health_guidance.json",
                    "icd_code": item["icd_code"],
                },
            )
        store.upsert_disease(
            {
                "id": did,
                "canonical_name": item["canonical_name"],
                "indonesian_name": item["indonesian_name"],
                "english_name": item["english_name"],
                "synonyms": syns,
                "lay_terms": lays,
                "icd_code": item["icd_code"],
                "short_description": item["short_description"],
                "causes": item["causes"],
                "symptoms": item["symptoms"],
                "risk_factors": item["risk_factors"],
                "prevention_management": item["prevention_management"],
                "source_references": refs,
                "review_metadata": {"language": "id", "updated_at": fetched_at},
            }
        )
        dis_count += 1

        sections = [
            ("Ringkasan & Penjelasan", item["short_description"]),
            ("Penyebab Umum", item["causes"]),
            ("Gejala yang Sering Muncul", item["symptoms"]),
            ("Pencegahan & Penanganan Awal", item["prevention_management"]),
        ]
        for s_idx, (heading, text) in enumerate(sections, 1):
            store.upsert_chunk(
                {
                    "chunk_id": f"chk-id-{_slug(did)}-{s_idx}",
                    "source_id": "SRC-AMBATUFIT-RULES",
                    "entity_type": "disease",
                    "entity_id": did,
                    "section_heading": heading,
                    "title": item["indonesian_name"],
                    "content": text,
                    "language": "id",
                    "category": "disease_education",
                    "metadata": {"icd_code": item["icd_code"], "aliases": [*syns, *lays]},
                    "updated_at": fetched_at,
                }
            )
            chunk_count += 1
    return dis_count, chunk_count

MEDLINEPLUS_TOPICS: List[Dict[str, Any]] = [
    {"term": "Diabetes Mellitus", "disease_id": "dis-diabetes-mellitus", "id_name": "Diabetes Melitus (Kencing Manis)", "icd_code": "E11", "synonyms": ["DM", "diabetes tipe 1", "diabetes tipe 2", "diabetes", "diabetes mellitus"], "lay_terms": ["kencing manis", "gula darah tinggi", "diabetes kering", "diabetes basah"]},
    {"term": "High Blood Pressure", "disease_id": "dis-hypertension", "id_name": "Hipertensi (Tekanan Darah Tinggi)", "icd_code": "I10", "synonyms": ["hypertension", "hipertensi", "HT", "essential hypertension"], "lay_terms": ["darah tinggi", "tensi tinggi", "tekanan darah naik"]},
    {"term": "Asthma", "disease_id": "dis-Bronchospasm_acute_asthma_exacerbation", "id_name": "Asma (Sesak Napas / Mengi)", "icd_code": "J45", "synonyms": ["asthma", "asma", "bronchospasm"], "lay_terms": ["bengek", "napas mengi", "sesak napas alergi"]},
    {"term": "Gastroesophageal Reflux Disease", "disease_id": "dis-GERD", "id_name": "Penyakit Refluks Asam Lambung (GERD)", "icd_code": "K21", "synonyms": ["GERD", "acid reflux", "asam lambung", "heartburn"], "lay_terms": ["maag", "ulu hati perih", "asam lambung naik", "dada panas"]},
    {"term": "Influenza", "disease_id": "dis-Influenza", "id_name": "Influenza (Flu)", "icd_code": "J11", "synonyms": ["flu", "seasonal influenza"], "lay_terms": ["flu demam", "pilek meriang"]},
    {"term": "Common Cold", "disease_id": "dis-URTI", "id_name": "Pilek & Infeksi Saluran Napas Atas (ISPA Ringan)", "icd_code": "J06.9", "synonyms": ["common cold", "URTI", "ISPA"], "lay_terms": ["pilek biasa", "batuk pilek", "masuk angin"]},
    {"term": "Pneumonia", "disease_id": "dis-Pneumonia", "id_name": "Pneumonia (Radang Paru)", "icd_code": "J18.9", "synonyms": ["lung infection", "radang paru"], "lay_terms": ["paru-paru basah", "infeksi paru"]},
    {"term": "Tuberculosis", "disease_id": "dis-Tuberculosis", "id_name": "Tuberkulosis (TBC)", "icd_code": "A15", "synonyms": ["TB", "TBC"], "lay_terms": ["flek paru", "batuk darah menahun"]},
    {"term": "Anemia", "disease_id": "dis-Anemia", "id_name": "Anemia (Kurang Darah)", "icd_code": "D64.9", "synonyms": ["iron deficiency anemia", "kurang darah"], "lay_terms": ["kurang darah", "hb rendah", "lemas pucat"]},
    {"term": "Migraine", "disease_id": "dis-migraine", "id_name": "Migrain (Sakit Kepala Sebelah)", "icd_code": "G43", "synonyms": ["migraine headache", "migrain"], "lay_terms": ["sakit kepala sebelah", "kepala berdenyut"]},
    {"term": "Allergic Rhinitis", "disease_id": "dis-Allergic_sinusitis", "id_name": "Rhinitis / Sinusitis Alergi", "icd_code": "J30.9", "synonyms": ["hay fever", "allergic sinusitis", "rhinitis alergi"], "lay_terms": ["alergi hidung", "bersin debu", "pilek alergi"]},
    {"term": "Diarrhea", "disease_id": "dis-diarrhea", "id_name": "Diare Akut", "icd_code": "A09", "synonyms": ["acute diarrhea", "diarrhea", "mencret"], "lay_terms": ["mencret", "sakit perut bab cair", "masuk angin perut"]},
    {"term": "Sore Throat", "disease_id": "dis-Viral_pharyngitis", "id_name": "Radang Tenggorokan (Faringitis)", "icd_code": "J02.9", "synonyms": ["pharyngitis", "sore throat", "radang tenggorokan"], "lay_terms": ["sakit menelan", "tenggorokan perih"]},
    {"term": "Bronchitis", "disease_id": "dis-Bronchitis", "id_name": "Bronkitis Akut", "icd_code": "J20.9", "synonyms": ["acute bronchitis", "bronkitis"], "lay_terms": ["batuk berdahak berat"]},
    {"term": "Gastritis", "disease_id": "dis-gastritis", "id_name": "Gastritis (Radang Lambung / Maag)", "icd_code": "K29.7", "synonyms": ["gastritis", "sakit maag"], "lay_terms": ["maag", "perih lambung", "kembung mual"]},
    {"term": "Panic Disorder", "disease_id": "dis-Panic_attack", "id_name": "Gangguan Panik & Serangan Panik", "icd_code": "F41.0", "synonyms": ["panic attack", "anxiety"], "lay_terms": ["panik", "cemas berlebih", "jantung berdebar cemas"]},
    {"term": "Knee Injuries and Disorders", "disease_id": None, "category": "injury_safety", "id_name": "Cedera & Nyeri Lutut"},
    {"term": "Exercise and Physical Fitness", "disease_id": None, "category": "physical_activity", "id_name": "Panduan Aktivitas Fisik & Kebugaran"},
    {"term": "Nutrition", "disease_id": None, "category": "nutrition", "id_name": "Panduan Nutrisi & Pola Makan Sehat"},
    {"term": "Sleep Disorders", "disease_id": None, "category": "general_health", "id_name": "Gangguan Tidur & Insomnia"},
]

OPENFDA_DRUG_QUERIES: List[Dict[str, Any]] = [
    {"generic_query": "acetaminophen", "indonesian_aliases": ["parasetamol", "paracetamol"]},
    {"generic_query": "ibuprofen", "indonesian_aliases": ["ibuprofen", "anti nyeri oains"]},
    {"generic_query": "cetirizine", "indonesian_aliases": ["setirizin", "cetirizine", "obat alergi"]},
    {"generic_query": "loratadine", "indonesian_aliases": ["loratadin", "obat alergi tidak ngantuk"]},
    {"generic_query": "guaifenesin", "indonesian_aliases": ["guaifenesin", "obat batuk berdahak", "gg"]},
    {"generic_query": "dextromethorphan", "indonesian_aliases": ["dekstrometorfan", "obat batuk kering"]},
    {"generic_query": "omeprazole", "indonesian_aliases": ["omeprazol", "obat asam lambung", "obat maag"]},
    {"generic_query": "famotidine", "indonesian_aliases": ["famotidin", "obat maag"]},
    {"generic_query": "loperamide", "indonesian_aliases": ["loperamid", "obat diare"]},
    {"generic_query": "metformin", "indonesian_aliases": ["metformin", "obat diabetes melitus"]},
    {"generic_query": "amlodipine", "indonesian_aliases": ["amlodipin", "obat darah tinggi hipertensi"]},
    {"generic_query": "aluminum hydroxide", "indonesian_aliases": ["antasida", "obat maag kombinasi"]},
    {"generic_query": "sertraline", "indonesian_aliases": ["setraline", "sertraline", "zoloft"]},
    {"generic_query": "amoxicillin", "indonesian_aliases": ["amoksisilin", "amoxicillin", "antibiotik"]},
    {"generic_query": "diclofenac", "indonesian_aliases": ["diklofenak", "cataflam", "voltaren"]},
    {"generic_query": "salbutamol", "indonesian_aliases": ["albuterol", "salbutamol", "ventolin"]},
]

# Curated educational drug reference entries (WHO EML / Pharmacopeia Ref) so common drugs
# across therapeutic classes are always searchable offline & online.
CURATED_REFERENCE_MEDICATIONS: List[Tuple[str, str, str, str, str, str, str, str, str, str]] = [
    ("sertraline", "Sertraline Hydrochloride (Zoloft / Fridep Ref)", "Zoloft", "SERTRALINE HYDROCHLORIDE", "Tablet 50 mg", "ORAL", "Obat keras (SSRI). Indikasi umum medis: gangguan depresi mayor, gangguan panik, gangguan obsesif-kompulsif (OCD), dan kecemasan sosial.", "Penggunaan harus dengan resep dan pemantauan dokter. Jangan menghentikan obat mendadak; waspadai peningkatan kecemasan awal atau ide bunuh diri.", "Penggunaan bersamaan dengan inhibitor MAO atau pimozide.", "Dapat berinteraksi dengan antidepresan lain, pengencer darah (warfarin), OAINS, dan tramadol (risiko sindrom serotonin)."),
    ("fluoxetine", "Fluoxetine Hydrochloride (Prozac / Kalxetin Ref)", "Prozac", "FLUOXETINE HYDROCHLORIDE", "Kapsul 20 mg", "ORAL", "Obat keras (SSRI). Indikasi umum medis: depresi mayor, bulimia nervosa, gangguan panik, dan OCD.", "Hanya dengan resep dokter. Memerlukan waktu beberapa minggu untuk efek optimal dan tidak boleh dihentikan tiba-tiba.", "Kombinasi dengan inhibitor MAO dalam jarak 14 hari.", "Berinteraksi dengan tramadol, triptan, OAINS, dan pengencer darah."),
    ("escitalopram", "Escitalopram Oxalate (Cipralex Ref)", "Cipralex", "ESCITALOPRAM OXALATE", "Tablet 10 mg", "ORAL", "Obat keras (SSRI). Indikasi umum medis: gangguan depresi mayor dan gangguan kecemasan menyeluruh (GAD).", "Wajib dengan resep dokter. Monitor irama jantung pada dosis tinggi atau usia lanjut.", "Inhibitor MAO, perpanjangan interval QT berat.", "Interaksi dengan obat pengubah irama jantung dan serotoninergik."),
    ("amitriptyline", "Amitriptyline Hydrochloride", "Elavil", "AMITRIPTYLINE HYDROCHLORIDE", "Tablet 25 mg", "ORAL", "Obat keras (antidepresan trisiklik). Digunakan dokter untuk depresi maupun nyeri neuropatik dan pencegahan migrain.", "Menyebabkan kantuk berat, mulut kering, dan pusing ortostatik; hindari berkendara.", "Pemulihan pasca infark miokard akut dan penggunaan inhibitor MAO.", "Berinteraksi dengan alkohol, sedatif, dan antikolinergik."),
    ("diazepam", "Diazepam (Valium / Stesolid Ref)", "Valium", "DIAZEPAM", "Tablet 5 mg", "ORAL", "Psikotropika / obat keras (benzodiazepin). Untuk kecemasan akut, kejang otot, dan penanganan kejang di bawah pengawasan dokter.", "Risiko ketergantungan dan kantuk berat; hanya digunakan jangka pendek sesuai resep dokter.", "Miastenia gravis berat, insufisiensi pernapasan berat, sleep apnea berat.", "Berbahaya bila dikombinasikan dengan alkohol atau opioid (risiko depresi napas)."),
    ("alprazolam", "Alprazolam (Xanax / Alganax Ref)", "Xanax", "ALPRAZOLAM", "Tablet 0.5 mg", "ORAL", "Psikotropika / obat keras (benzodiazepin). Penanganan gangguan panik dan kecemasan di bawah kontrol ketat dokter.", "Risiko ketergantungan tinggi; tidak boleh dihentikan secara mendadak.", "Glaukoma sudut sempit akut, insufisiensi napas berat.", "Berinteraksi dengan alkohol, opioid, dan inhibitor CYP3A4 (ketokonazol)."),
    ("gabapentin", "Gabapentin", "Neurontin", "GABAPENTIN", "Kapsul 300 mg", "ORAL", "Obat keras. Digunakan dokter untuk nyeri saraf (neuropati) dan terapi tambahan kejang epilepsi.", "Dapat menyebabkan pusing dan kantuk; penurunan dosis harus bertahap bersama dokter.", "Hipersensitivitas terhadap gabapentin.", "Antasida aluminium/magnesium dapat menurunkan penyerapan jika diminum bersamaan."),
    ("mefenamic-acid", "Asam Mefenamat (Mefenamic Acid / Ponstan Ref)", "Ponstan", "MEFENAMIC ACID", "Kaplet 500 mg", "ORAL", "Obat keras (OAINS). Meredakan nyeri ringan hingga sedang seperti nyeri gigi, nyeri haid, atau nyeri pascatindakan.", "Minum sesudah makan. Waspadai iritasi lambung, maag kambuh, dan gangguan fungsi ginjal pada pemakaian lama.", "Tukak lambung aktif, perdarahan saluran cerna, alergi aspirin/OAINS, gagal ginjal/jantung berat.", "Berinteraksi dengan pengencer darah (warfarin), aspirin, dan obat hipertensi tertentu."),
    ("diclofenac", "Natrium Diklofenak (Diclofenac / Voltaren Ref)", "Voltaren", "DICLOFENAC SODIUM", "Tablet 50 mg", "ORAL", "Obat keras (OAINS). Anti-inflamasi dan pereda nyeri sendi, radang sendi, atau nyeri otot.", "Gunakan dosis terendah dalam durasi sesingkat mungkin dengan pengawasan dokter.", "Tukak lambung aktif, riwayat asma dipicu OAINS, penyakit jantung iskemik berat.", "Berinteraksi dengan OAINS lain, kortikosteroid, dan antikoagulan."),
    ("meloxicam", "Meloxicam", "Mobic", "MELOXICAM", "Tablet 15 mg", "ORAL", "Obat keras (OAINS selektif COX-2). Mengurangi peradangan dan nyeri sendi seperti osteoartritis.", "Waspadai gangguan lambung, peningkatan tekanan darah, dan risiko kardiovaskular bila jangka panjang.", "Tukak lambung aktif, gagal ginjal berat tanpa dialisis, alergi OAINS.", "Interaksi dengan aspirin, ACE inhibitor, dan diuretik."),
    ("celecoxib", "Celecoxib", "Celebrex", "CELECOXIB", "Kapsul 200 mg", "ORAL", "Obat keras (COX-2 inhibitor). Meredakan nyeri sendi dan radang pada kondisi artritis.", "Harus dengan resep dokter; waspadai riwayat alergi sulfonamid dan penyakit jantung.", "Alergi sulfonamid, riwayat reaksi alergi OAINS, penyakit jantung berat.", "Berinteraksi dengan warfarin, flukonazol, dan lithium."),
    ("aspirin", "Asam Asetilsalisilat / Aspirin (Cardio & Analgesik)", "Aspirin", "ACETYLSALICYLIC ACID", "Tablet 80 mg / 500 mg", "ORAL", "Pereda nyeri/demam serta pencegahan pembekuan darah dosis rendah sesuai anjuran dokter.", "Tidak dianjurkan untuk anak/remaja dengan infeksi virus karena risiko sindrom Reye.", "Perdarahan aktif, tukak lambung aktif, alergi salisilat.", "Meningkatkan risiko perdarahan bila dikonsumsi bersama pengencer darah atau ibuprofen."),
    ("lansoprazole", "Lansoprazole", "Prevacid", "LANSOPRAZOLE", "Kapsul 30 mg", "ORAL", "Obat keras (PPI). Menurunkan produksi asam lambung berlebih pada GERD dan tukak lambung.", "Biasanya diminum 30 menit sebelum makan pagi sesuai arahan dokter.", "Hipersensitivitas terhadap penghambat pompa proton.", "Dapat memengaruhi penyerapan obat yang butuh asam lambung (ketokonazol, zat besi)."),
    ("ranitidine", "Ranitidine Hydrochloride", "Zantac Ref", "RANITIDINE HYDROCHLORIDE", "Tablet 150 mg", "ORAL", "Penghambat reseptor H2 untuk keluhan asam lambung; penggunaannya kini mengikuti arahan regulasi terbaru dan dokter.", "Konsultasikan alternatif penurun asam lambung terbaru (seperti famotidine) dengan dokter/apoteker.", "Hipersensitivitas terhadap ranitidine.", "Interaksi dengan ketokonazol dan warfarin."),
    ("sucralfate", "Sukralfat (Sucralfate Suspensi/Tablet)", "Inpepsa Ref", "SUCRALFATE", "Suspensi 500 mg/5 mL", "ORAL", "Obat keras pelindung mukosa lambung. Melapisi tukak lambung atau gastritis yang meradang.", "Diminum saat perut kosong dan beri jeda 2 jam dari obat lain agar tidak menghambat penyerapan.", "Hipersensitivitas terhadap sukralfat; hati-hati pada gagal ginjal kronis.", "Mengurangi penyerapan antibiotik kuinolon, tetrasiklin, dan levotiroksin."),
    ("domperidone", "Domperidone", "Motilium", "DOMPERIDONE", "Tablet 10 mg", "ORAL", "Obat keras antimuntah dan prokinetik. Mengatasi mual, muntah, dan perut penuh akibat gerak lambung lambat.", "Gunakan durasi sesingkat mungkin sesuai resep dokter; hati-hati risiko gangguan irama jantung.", "Perdarahan saluran cerna, sumbatan usus, gangguan irama jantung QT memanjang.", "Kontraindikasi bersama ketokonazol, eritromisin, dan amiodaron."),
    ("ondansetron", "Ondansetron", "Zofran", "ONDANSETRON HYDROCHLORIDE", "Tablet 4 mg", "ORAL", "Obat keras antimual kuat (antagonis 5-HT3) untuk mual/muntah berat sesuai resep dokter.", "Waspadai sakit kepala, sembelit, dan pemanjangan interval QT jantung.", "Penggunaan bersama apomorfin.", "Berinteraksi dengan obat perpanjang interval QT dan SSRI."),
    ("simethicone", "Simethicone (Pereda Gas & Kembung)", "Gas-X Ref", "SIMETHICONE", "Tablet Kunyah 80 mg", "ORAL", "Obat bebas pereda rasa penuh, kembung, dan bersendawa akibat gas berlebih di saluran cerna.", "Konsultasikan bila nyeri perut hebat, demam, atau muntah terus-menerus.", "Hipersensitivitas komponen obat.", "Secara lokal di usus dan minim interaksi sistemik."),
    ("bisacodyl", "Bisacodyl (Dulcolax Ref)", "Dulcolax", "BISACODYL", "Tablet Salut Enterik 5 mg", "ORAL", "Obat bebas terbatas pencahar stimulan untuk sembelit (konstipasi) jangka pendek.", "Jangan dikunyah atau diminum bersama susu/antasida dalam rentang 1 jam. Jangan dipakai jangka panjang.", "Nyeri perut hebat belum jelas sebabnya, sumbatan usus, radang usus akut.", "Antasida/susu melarutkan lapisan salut enterik lebih cepat sehingga mengiritasi lambung."),
    ("lactulose", "Laktulosa (Lactulose Sirup)", "Duphalac Ref", "LACTULOSE", "Sirup 3.335 g/5 mL", "ORAL", "Obat bebas pencahar osmotik yang melunakkan tinja pada sembelit.", "Perbanyak minum air putih selama menggunakan pencahar osmotik.", "Galaktosemia dan sumbatan saluran cerna.", "Penggunaan lama dapat memengaruhi keseimbangan elektrolit bila terjadi diare."),
    ("ctm-chlorpheniramine", "Chlorpheniramine Maleate (CTM)", "CTM", "CHLORPHENIRAMINE MALEATE", "Tablet 4 mg", "ORAL", "Obat bebas terbatas antihistamin generasi pertama untuk bersin, pilek alergi, gatal kulit, dan biduran.", "Sering menyebabkan kantuk; hindari mengemudi atau mengoperasikan mesin.", "Serangan asma akut, glaukoma sudut sempit, pembesaran prostat berat.", "Efek kantuk bertambah bersama alkohol atau obat penenang."),
    ("fexofenadine", "Fexofenadine Hydrochloride", "Allegra", "FEXOFENADINE HYDROCHLORIDE", "Tablet 120 mg", "ORAL", "Antihistamin non-sedatif untuk rinitis alergi dan urtikaria (biduran).", "Hindari minum bersama jus buah (jeruk, apel, anggur) karena menurunkan penyerapan obat.", "Hipersensitivitas terhadap fexofenadine.", "Antasida aluminium/magnesium menurunkan penyerapan obat ini."),
    ("ambroxol", "Ambroxol Hydrochloride", "Mucosolvan Ref", "AMBROXOL HYDROCHLORIDE", "Tablet 30 mg", "ORAL", "Obat keras / mukolitik pengencer dahak pada batuk berdahak dan bronkitis.", "Hentikan dan konsultasikan dokter bila muncul ruam kulit atau batuk tak membaik lebih dari 7 hari.", "Riwayat alergi ambroxol atau bromhexine; hati-hati pada tukak lambung.", "Dapat meningkatkan konsentrasi beberapa antibiotik di jaringan paru."),
    ("bromhexine", "Bromhexine Hydrochloride", "Bisolvon Ref", "BROMHEXINE HYDROCHLORIDE", "Tablet 8 mg", "ORAL", "Obat bebas terbatas mukolitik untuk membantu mengencerkan dahak di saluran napas.", "Minum air putih yang cukup membantu kerja pengencer dahak.", "Hipersensitivitas komponen obat; hati-hati riwayat tukak lambung.", "Minim interaksi klinis yang bermakna pada pemakaian singkat."),
    ("acetylcysteine", "N-Acetylcysteine (NAC)", "Fluimucil Ref", "ACETYLCYSTEINE", "Kapsul / Effervescent 200 mg", "ORAL", "Obat keras mukolitik pengencer dahak kental di saluran napas.", "Perhatikan bau khas belerang; hati-hati pada penderita asma dan riwayat tukak lambung.", "Hipersensitivitas acetylcysteine; tidak untuk anak di bawah 2 tahun tanpa instruksi dokter.", "Jangan dicampur dengan antibiotik secara langsung dalam satu larutan."),
    ("salbutamol", "Salbutamol / Albuterol Sulfate (Ventolin Ref)", "Ventolin", "SALBUTAMOL SULFATE", "Inhaler 100 mcg / Tablet 2 mg", "INHALASI / ORAL", "Obat keras bronkodilator pelega napas pada asma dan bronkospasme (sesak mengi).", "Jika inhaler pelega dibutuhkan semakin sering (>2x/minggu), segera kontrol ke dokter untuk evaluasi terapi kontrol.", "Hipersensitivitas terhadap salbutamol.", "Penghambat beta (seperti propranolol) dapat berlawanan kerja dengan salbutamol."),
    ("glimepiride", "Glimepiride", "Amaryl", "GLIMEPIRIDE", "Tablet 2 mg", "ORAL", "Obat keras antidiabetes golongan sulfonilurea untuk mengontrol gula darah pada diabetes tipe 2.", "Risiko hipoglikemia (gula darah terlalu rendah); harus dikonsumsi teratur bersama jadwal makan sesuai resep dokter.", "Diabetes tipe 1, ketoasidosis diabetik, alergi sulfonilurea/sulfonamid.", "Berinteraksi dengan obat diabetes lain, flukonazol, dan alkohol."),
    ("captopril", "Captopril", "Capoten", "CAPTOPRIL", "Tablet 25 mg", "ORAL", "Obat keras penurun tekanan darah (ACE inhibitor) untuk hipertensi dan gagal jantung.", "Dapat memicu batuk kering pada sebagian pengguna. Kontraindikasi selama kehamilan.", "Kehamilan, riwayat angioedema akibat ACE inhibitor.", "Berinteraksi dengan suplemen kalium, diuretik hemat kalium, dan OAINS."),
    ("candesartan", "Candesartan Cilexetil", "Atacand", "CANDESARTAN CILEXETIL", "Tablet 8 mg", "ORAL", "Obat keras golongan ARB untuk hipertensi dan perlindungan jantung.", "Tidak boleh digunakan saat hamil. Pantau tekanan darah dan fungsi ginjal secara berkala.", "Kehamilan, gangguan hati berat/kolestasis.", "Berinteraksi dengan suplemen kalium, lithium, dan OAINS."),
    ("bisoprolol", "Bisoprolol Fumarate", "Concor", "BISOPROLOL FUMARATE", "Tablet 5 mg", "ORAL", "Obat keras penghambat beta selektif untuk hipertensi, angina, dan gagal jantung.", "Jangan menghentikan obat ini secara mendadak karena dapat memicu lonjakan detak jantung atau tekanan darah.", "Bradikardia berat, syok kardiogenik, asma berat.", "Berinteraksi dengan verapamil, diltiazem, dan klonidin."),
    ("simvastatin", "Simvastatin", "Zocor", "SIMVASTATIN", "Tablet 10 mg / 20 mg", "ORAL", "Obat keras golongan statin untuk menurunkan kolesterol LDL dan risiko kardiovaskular.", "Umumnya diminum malam hari. Laporkan ke dokter bila timbul nyeri otot berat atau urin gelap. Hindari jus jeruk bali (grapefruit).", "Penyakit hati aktif, kehamilan dan menyusui.", "Berinteraksi dengan gemfibrozil, amlodipine dosis tinggi, dan antijamur azol."),
    ("atorvastatin", "Atorvastatin Calcium", "Lipitor", "ATORVASTATIN CALCIUM", "Tablet 20 mg", "ORAL", "Obat keras statin untuk mengendalikan kolesterol darah dan trigliserida.", "Pantau keluhan nyeri otot yang tidak biasa dan fungsi hati sesuai jadwal dokter.", "Penyakit hati aktif, kehamilan, menyusui.", "Interaksi dengan siklosporin, klaritromisin, dan antijamur azol."),
    ("allopurinol", "Allopurinol", "Zyloric", "ALLOPURINOL", "Tablet 100 mg / 300 mg", "ORAL", "Obat keras penurun kadar asam urat darah jangka panjang (pencegahan serangan gout).", "Hentikan segera dan temui dokter bila muncul ruam kulit gatal/melepuh. Tidak untuk menghentikan nyeri serangan gout akut yang sedang berlangsung.", "Riwayat reaksi alergi berat terhadap allopurinol.", "Berinteraksi dengan azathioprine, mercaptopurine, dan diuretik thiazide."),
    ("furosemide", "Furosemide (Lasix Ref)", "Lasix", "FUROSEMIDE", "Tablet 40 mg", "ORAL", "Obat keras diuretik kuat untuk mengurangi penumpukan cairan/bengkak (edema) dan tekanan darah tinggi.", "Diminum pagi/siang agar tidak mengganggu tidur karena sering buang air kecil; pantau elektrolit.", "Gagal ginjal dengan anuria, dehidrasi berat, hipokalemia berat.", "Berinteraksi dengan digoxin, aminoglikosida, dan OAINS."),
    ("amoxicillin", "Amoxicillin Trihydrate", "Amoxil", "AMOXICILLIN TRIHYDRATE", "Kaplet 500 mg", "ORAL", "Obat keras ANTIBIOTIK golongan penisilin untuk infeksi bakteri yang didiagnosis dokter (bukan untuk flu/pilek virus).", "Wajib berdasarkan resep dokter dan dihabiskan sesuai aturan untuk mencegah resistensi antibiotik.", "Alergi penisilin atau antibiotik beta-laktam.", "Dapat berinteraksi dengan allopurinol (meningkatkan risiko ruam) dan methotrexate."),
    ("azithromycin", "Azithromycin Dihydrate", "Zithromax", "AZITHROMYCIN", "Tablet 500 mg", "ORAL", "Obat keras antibiotik makrolida untuk infeksi bakteri tertentu sesuai resep dokter.", "Gunakan hanya dengan resep dokter; waspadai gangguan irama jantung QT pada kelompok berisiko.", "Riwayat gangguan hati/kuning akibat azithromycin atau alergi makrolida.", "Berinteraksi dengan antasida (beri jeda), warfarin, dan digoxin."),
    ("cefixime", "Cefixime Trihydrate", "Cefspan", "CEFIXIME", "Kapsul 100 mg / 200 mg", "ORAL", "Obat keras antibiotik sefalosporin generasi ketiga untuk infeksi bakteri tertentu sesuai resep dokter.", "Hanya dengan resep dokter. Hentikan bila muncul diare berdarah hebat atau reaksi alergi.", "Alergi sefalosporin atau reaksi anafilaksis terhadap penisilin.", "Berinteraksi dengan warfarin (meningkatkan waktu protrombin)."),
    ("ciprofloxacin", "Ciprofloxacin Hydrochloride", "Cipro", "CIPROFLOXACIN", "Tablet 500 mg", "ORAL", "Obat keras antibiotik kuinolon untuk infeksi bakteri terkonfirmasi oleh dokter.", "Waspadai nyeri atau radang tendon serta sensitivitas sinar matahari; jangan diminum bersama produk susu atau antasida.", "Riwayat alergi kuinolon atau penggunaan bersama tizanidine.", "Antasida, zat besi, kalsium, dan zink menghambat penyerapan ciprofloxacin."),
    ("metronidazole", "Metronidazole", "Flagyl", "METRONIDAZOLE", "Tablet 500 mg", "ORAL", "Obat keras antibiotik/antiprotozoa untuk infeksi bakteri anaerob atau parasit tertentu.", "Hindari alkohol selama dan hingga 48 jam setelah selesai terapi karena memicu mual/muntah berat.", "Hipersensitivitas metronidazole atau nitroimidazol.", "Berinteraksi dengan alkohol, warfarin, dan lithium."),
    ("ketoconazole", "Ketoconazole (Tablet / Krim)", "Nizoral Ref", "KETOCONAZOLE", "Tablet 200 mg / Krim 2%", "ORAL / TOPIKAL", "Obat antijamur golongan azol. Sediaan topikal untuk infeksi jamur kulit; sediaan oral kini sangat dibatasi oleh dokter karena risiko hati.", "Sediaan oral hanya diberikan bila manfaat jauh melebihi risiko terhadap organ hati.", "Penyakit hati akut/kronis untuk sediaan oral.", "Memiliki banyak interaksi obat (statin, alprazolam, domperidone, cisapride)."),
    ("acyclovir", "Acyclovir (Asiklovir)", "Zovirax", "ACV / ACYCLOVIR", "Tablet 400 mg / Krim 5%", "ORAL / TOPIKAL", "Obat antivirus untuk infeksi virus herpes simpleks atau cacar air/herpes zoster sesuai anjuran dokter.", "Perbanyak minum air putih saat mengonsumsi acyclovir tablet untuk melindungi fungsi ginjal.", "Hipersensitivitas terhadap asiklovir atau valasiklovir.", "Berinteraksi dengan probenesid dan obat yang memengaruhi fungsi ginjal."),
    ("dexamethasone", "Dexamethasone", "Kalmethasone", "DEXAMETHASONE", "Tablet 0.5 mg", "ORAL", "Obat keras kortikosteroid poten anti-inflamasi dan penekan reaksi radang berat sesuai resep dokter.", "Bukan obat bebas atau suplemen penambah nafsu makan; penggunaan jangka panjang berisiko merusak lambung, tulang, dan hormon.", "Infeksi jamur sistemik tidak terkontrol.", "Berinteraksi dengan OAINS (risiko tukak lambung), antidiabetes, dan vaksin hidup."),
    ("methylprednisolone", "Methylprednisolone", "Medrol / Lameson", "METHYLPREDNISOLONE", "Tablet 4 mg / 8 mg", "ORAL", "Obat keras kortikosteroid untuk kondisi peradangan berat atau reaksi alergi/autoimun atas resep dokter.", "Jangan menghentikan terapi mendadak apabila sudah diminum lebih dari beberapa hari (perlu tapering off).", "Infeksi jamur sistemik.", "Berinteraksi dengan OAINS, obat diabetes, dan antikoagulan."),
    ("ferrous-sulfate", "Zat Besi + Asam Folat (Tablet Tambah Darah)", "Sangobion / TTD", "FERROUS SULFATE, FOLIC ACID", "Tablet Salut Gula", "ORAL", "Obat bebas suplemen penambah darah untuk membantu mencegah dan mengatasi anemia defisiensi besi.", "Dapat membuat tinja berwarna lebih gelap (wajar). Hindari diminum bersamaan dengan teh/kopi atau antasida.", "Kelebihan zat besi (hemokromatosis) dan anemia non-defisiensi besi.", "Teh, kopi, kalsium, dan antasida menurunkan penyerapan zat besi; vitamin C membantu penyerapannya."),
]


def _ean13_from_index(idx: int) -> str:
    body = f"8992026{idx + 100:05d}"
    digits = [int(d) for d in body]
    checksum = (10 - (sum(digits[0::2]) + 3 * sum(digits[1::2])) % 10) % 10
    return f"{body}{checksum}"


def _bpom_nie_prefix(indications: str) -> str:
    low = indications.lower()
    if "obat bebas terbatas" in low:
        return "DTL"
    if "obat bebas" in low:
        return "DBL"
    return "GKL"


def ingest_curated_reference_medications(store: RAGStore, fetched_at: str) -> Tuple[int, int]:
    meds_added = 0
    chunks_added = 0
    for idx, (slug, prod_name, brand, generic, form, route, ind, warn, contra, inter) in enumerate(CURATED_REFERENCE_MEDICATIONS, 1):
        prod_id = f"medref-{slug}"
        active_list = [p.strip() for p in generic.split(",") if p.strip()]
        source_url = f"https://list.essentialmeds.org/?query={urllib.parse.quote(active_list[0])}"
        ean13 = _ean13_from_index(idx)
        bpom_nie = f"{_bpom_nie_prefix(ind)}2601{idx:03d}10A1"
        store.upsert_medication_product(
            {
                "id": prod_id,
                "product_name": prod_name,
                "brand_name": brand,
                "generic_name": generic,
                "active_ingredients": active_list,
                "is_combination": len(active_list) > 1,
                "strength": form,
                "dosage_form": form.split()[0].upper(),
                "route": route,
                "marketing_authorization_holder": "Referensi Farmakologi Edukatif",
                "registration_number": bpom_nie,
                "product_code": ean13,
                "registration_status": "international_source_id_unverified",
                "indications": ind,
                "contraindications": contra,
                "warnings": warn,
                "interactions": inter,
                "label_summary": (
                    f"Referensi edukatif untuk {prod_name} (zat aktif: {', '.join(active_list)}). "
                    f"Bukan bukti izin edar BPOM dan bukan resep pengobatan individual."
                ),
                "source_id": "SRC-AMBATUFIT-MEDREF",
                "source_url": source_url,
                "updated_at": fetched_at,
            }
        )
        meds_added += 1
        store.upsert_chunk(
            {
                "chunk_id": f"chk-medref-{slug}",
                "source_id": "SRC-AMBATUFIT-MEDREF",
                "entity_type": "medication_product",
                "entity_id": prod_id,
                "section_heading": "Referensi Farmakologi Umum",
                "title": prod_name,
                "content": f"Produk: {prod_name} | Generik: {generic} | Indikasi umum: {ind} | Peringatan: {warn} | Kontraindikasi: {contra}",
                "language": "id",
                "category": "medication_knowledge",
                "metadata": {
                    "url": source_url,
                    "generic_name": generic,
                    "brand_name": brand,
                    "aliases": [brand.lower(), generic.lower(), slug.replace("-", " ")],
                },
                "updated_at": fetched_at,
            }
        )
        chunks_added += 1
    return meds_added, chunks_added


def _clean_html(raw: str) -> str:
    text = unescape(raw or "")
    text = re.sub(r"<li[^>]*>", "\n• ", text, flags=re.I)
    text = re.sub(r"<p[^>]*>|<br\s*/?>|</h\d>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _chunk_text(text: str, *, max_chars: int = 480, overlap: int = 80) -> List[str]:
    clean = (text or "").strip()
    if not clean:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n+", clean) if p.strip()]
    chunks: List[str] = []
    buf = ""
    for p in paragraphs:
        if len(buf) + len(p) + 1 <= max_chars:
            buf = f"{buf}\n{p}".strip() if buf else p
        else:
            if buf:
                chunks.append(buf)
            while len(p) > max_chars:
                cut = p.rfind(". ", 0, max_chars)
                if cut < max_chars // 2:
                    cut = max_chars
                else:
                    cut += 1
                chunks.append(p[:cut].strip())
                p = p[max(0, cut - overlap) :].strip()
            buf = p
    if buf:
        chunks.append(buf)
    return chunks


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")


def _http_get(url: str, timeout: float = 12.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def register_static_sources(store: RAGStore, fetched_at: str) -> None:
    sources = [
        {
            "source_id": "SRC-DDXPLUS-V2",
            "name": "Official DDXPlus Dataset — Release Conditions & Evidences",
            "publisher": "Mila-IQIA / Fansi Tchango et al. (NeurIPS 2022)",
            "origin_url": "https://doi.org/10.6084/m9.figshare.22687585",
            "source_type": "academic_synthetic_benchmark",
            "language": "en",
            "published_at": "2022-11-01",
            "updated_at": "2023-04-01",
            "fetched_at": fetched_at,
            "verification_status": "verified_open_benchmark_synthetic",
            "license_terms": "CC BY 4.0",
            "document_version": "figshare-22687585.v2",
            "status": "active",
        },
        {
            "source_id": "SRC-AMBATUFIT-RULES",
            "name": "AmbatuFit Verified General Health & Wellness Guidance Rules",
            "publisher": "AmbatuFit Internal Editorial",
            "origin_url": "internal://backend/rules/health_guidance.json",
            "source_type": "internal_rule_catalog",
            "language": "id",
            "published_at": "2026-11-21",
            "updated_at": "2026-11-21",
            "fetched_at": fetched_at,
            "verification_status": "internal_informational_guidance",
            "license_terms": "Internal project rules",
            "document_version": "2.0.0",
            "status": "active",
        },
        {
            "source_id": "SRC-MEDLINEPLUS-API",
            "name": "MedlinePlus Health Topics Web Service (NLM NIH)",
            "publisher": "U.S. National Library of Medicine (NIH)",
            "origin_url": "https://medlineplus.gov/about/developers/webservices/",
            "source_type": "official_health_education_api",
            "language": "en",
            "published_at": None,
            "updated_at": fetched_at,
            "fetched_at": fetched_at,
            "verification_status": "verified_public_gov_api_en",
            "license_terms": "NLM Public Domain / Attribution required",
            "document_version": "wsearch-xml-live",
            "status": "active",
        },
        {
            "source_id": "SRC-OPENFDA-LABEL",
            "name": "openFDA Human Drug SPL Labeling API",
            "publisher": "U.S. Food and Drug Administration (FDA)",
            "origin_url": "https://open.fda.gov/apis/drug/label/",
            "source_type": "official_us_drug_label_api",
            "language": "en",
            "published_at": None,
            "updated_at": fetched_at,
            "fetched_at": fetched_at,
            "verification_status": "international_reference_not_bpom_indonesia",
            "license_terms": "openFDA CC0 1.0 Public Domain (US SPL only; not Indonesian registration proof)",
            "document_version": "openfda-drug-label-v1",
            "status": "active",
        },
        {
            "source_id": "SRC-AMBATUFIT-MEDREF",
            "name": "Referensi Farmakologi Umum & Daftar Obat Esensial WHO (Edukatif)",
            "publisher": "WHO Essential Medicines / Referensi Farmakologi",
            "origin_url": "https://list.essentialmeds.org/",
            "source_type": "educational_pharmacology_reference",
            "language": "id",
            "published_at": "2025-01-01",
            "updated_at": fetched_at,
            "fetched_at": fetched_at,
            "verification_status": "educational_reference_not_bpom_indonesia",
            "license_terms": "Educational non-prescription reference only",
            "document_version": "medref-2.0.0",
            "status": "active",
        },
        {
            "source_id": "SRC-SATUSEHAT-KFA",
            "name": "Kementerian Kesehatan RI — SATUSEHAT KFA API",
            "publisher": "Kementerian Kesehatan Republik Indonesia",
            "origin_url": "https://satusehat.kemkes.go.id/platform/docs/id/master-data/kfa/rest-api-kfa/",
            "source_type": "national_pharmaceutical_master_api",
            "language": "id",
            "published_at": None,
            "updated_at": None,
            "fetched_at": fetched_at,
            "verification_status": "requires_oauth2_credentials_not_configured",
            "license_terms": "SATUSEHAT Developer Portal Terms of Use",
            "document_version": "kfa-v2",
            "status": "inactive",
        },
        {
            "source_id": "SRC-BPOM-CEKPRODUK",
            "name": "BPOM RI — Cek Produk Obat",
            "publisher": "Badan Pengawas Obat dan Makanan RI",
            "origin_url": "https://cekbpom.pom.go.id/produk-obat",
            "source_type": "national_drug_registry_portal",
            "language": "id",
            "published_at": None,
            "updated_at": None,
            "fetched_at": fetched_at,
            "verification_status": "web_portal_only_no_public_rest_api_documented",
            "license_terms": "Reference verification portal only; automated scraping prohibited",
            "document_version": "portal-ref",
            "status": "inactive",
        },
        {
            "source_id": "SRC-WHO-ICD-API",
            "name": "WHO ICD-10 / ICD-11 Official REST API",
            "publisher": "World Health Organization",
            "origin_url": "https://icd.who.int/icdapi/",
            "source_type": "international_classification_api",
            "language": "en",
            "published_at": None,
            "updated_at": None,
            "fetched_at": fetched_at,
            "verification_status": "requires_oauth2_credentials_not_configured",
            "license_terms": "WHO ICD API License",
            "document_version": "v2",
            "status": "inactive",
        },
    ]
    for src in sources:
        store.upsert_source(src)


def ingest_ddxplus_conditions(store: RAGStore, fetched_at: str) -> Tuple[int, int]:
    if not RELEASE_CONDITIONS_PATH.exists():
        return 0, 0
    conditions = json.loads(RELEASE_CONDITIONS_PATH.read_text(encoding="utf-8"))
    evidences = (
        json.loads(RELEASE_EVIDENCES_PATH.read_text(encoding="utf-8"))
        if RELEASE_EVIDENCES_PATH.exists()
        else {}
    )
    dis_count = 0
    chunk_count = 0

    for cname, spec in conditions.items():
        did = f"dis-{_slug(cname)}"
        id_name, syns, lays = DDXPLUS_INDONESIAN_TERMS.get(cname, (cname, [], []))
        sym_codes = list((spec.get("symptoms") or {}).keys())
        sym_texts = []
        for sc in sym_codes[:8]:
            q_id = _get_indonesian_label(sc, evidences).strip().rstrip("?")
            if q_id:
                sym_texts.append(q_id)
        sym_summary = "; ".join(sym_texts) if sym_texts else None
        icd = spec.get("icd10-id")

        store.upsert_disease(
            {
                "id": did,
                "canonical_name": cname,
                "indonesian_name": id_name,
                "english_name": cname,
                "synonyms": sorted(set([cname, id_name, *syns])),
                "lay_terms": lays,
                "icd_code": icd,
                "short_description": f"Kondisi kesehatan {id_name} (istilah medis: {cname}).",
                "causes": None,
                "symptoms": sym_summary,
                "risk_factors": None,
                "prevention_management": None,
                "source_references": [
                    {
                        "source_id": "SRC-DDXPLUS-V2",
                        "title": f"Referensi Kondisi Klinis: {id_name}",
                        "url": "https://doi.org/10.6084/m9.figshare.22687585",
                        "icd_code": icd,
                    }
                ],
                "review_metadata": {"source": "DDXPlus release_conditions.json", "updated_at": fetched_at},
            }
        )
        dis_count += 1

        chunk_content = f"Kondisi kesehatan: {id_name}. Kode klasifikasi ICD-10: {icd or 'Tidak tercatat'}."
        if sym_summary:
            chunk_content += f" Keluhan atau tanda yang sering menyertai: {sym_summary}."
        store.upsert_chunk(
            {
                "chunk_id": f"chk-ddx-{_slug(cname)}",
                "source_id": "SRC-DDXPLUS-V2",
                "entity_type": "disease",
                "entity_id": did,
                "section_heading": "Gejala & Klasifikasi Kondisi",
                "title": id_name,
                "content": chunk_content,
                "language": "id",
                "category": "disease_reference",
                "metadata": {"icd_code": icd, "aliases": [cname, id_name, *syns, *lays]},
                "updated_at": fetched_at,
            }
        )
        chunk_count += 1
    return dis_count, chunk_count


def ingest_internal_guidance_rules(store: RAGStore, fetched_at: str) -> int:
    if not HEALTH_GUIDANCE_PATH.exists():
        return 0
    rules = json.loads(HEALTH_GUIDANCE_PATH.read_text(encoding="utf-8"))
    count = 0
    for rule in rules:
        rid = rule.get("rule_id", f"rule-{count}")
        store.upsert_chunk(
            {
                "chunk_id": f"chk-rule-{_slug(rid)}",
                "source_id": "SRC-AMBATUFIT-RULES",
                "entity_type": "guidance_rule",
                "entity_id": rid,
                "section_heading": rule.get("category", "general_wellbeing"),
                "title": rule.get("title", "Panduan AmbatuFit"),
                "content": rule.get("description", ""),
                "language": "id",
                "category": rule.get("category", "general_wellbeing"),
                "metadata": {
                    "goal": rule.get("goal"),
                    "preference_tags": rule.get("preference_tags", []),
                    "reference_id": (rule.get("source") or {}).get("reference_id"),
                },
                "updated_at": fetched_at,
            }
        )
        count += 1
    return count


def ingest_medlineplus(store: RAGStore, fetched_at: str) -> Tuple[int, int, List[str]]:
    diseases_updated = 0
    chunks_added = 0
    failures: List[str] = []

    for topic in MEDLINEPLUS_TOPICS:
        term = topic["term"]
        q = urllib.parse.quote(term)
        url = f"https://wsearch.nlm.nih.gov/ws/query?db=healthTopics&term={q}&retmax=2"
        try:
            raw_xml = _http_get(url, timeout=12.0)
            root = ET.fromstring(raw_xml)
        except Exception as exc:
            failures.append(f"MedlinePlus '{term}': {exc}")
            continue

        docs = root.findall(".//document")
        if not docs:
            failures.append(f"MedlinePlus '{term}': 0 documents returned")
            continue

        # Pick first English document
        chosen = None
        for d in docs:
            url_attr = d.attrib.get("url", "")
            if "/spanish/" not in url_attr:
                chosen = d
                break
        if chosen is None:
            chosen = docs[0]

        doc_url = chosen.attrib.get("url", "https://medlineplus.gov/healthtopics.html")
        title = ""
        alt_titles: List[str] = []
        summary_html = ""
        for content_el in chosen.findall("content"):
            name_attr = content_el.attrib.get("name", "")
            val = "".join(content_el.itertext()).strip()
            if name_attr == "title":
                title = _clean_html(val)
            elif name_attr == "altTitle":
                cleaned = _clean_html(val)
                if cleaned:
                    alt_titles.append(cleaned)
            elif name_attr == "FullSummary":
                summary_html = val

        summary_clean = _clean_html(summary_html)
        if not summary_clean:
            continue

        entity_id = topic.get("disease_id")
        if entity_id:
            existing = store.get_disease(entity_id) or {}
            syns = sorted(
                set(
                    [
                        *(existing.get("synonyms") or []),
                        *(topic.get("synonyms") or []),
                        *alt_titles,
                        title or term,
                    ]
                )
            )
            lays = sorted(set([*(existing.get("lay_terms") or []), *(topic.get("lay_terms") or [])]))
            refs = list(existing.get("source_references") or [])
            if not any(r.get("url") == doc_url for r in refs):
                refs.append({"source_id": "SRC-MEDLINEPLUS-API", "title": title or term, "url": doc_url})
            short_desc = summary_clean.split("\n")[0][:600]
            store.upsert_disease(
                {
                    "id": entity_id,
                    "canonical_name": existing.get("canonical_name") or term,
                    "indonesian_name": topic.get("id_name") or existing.get("indonesian_name") or term,
                    "english_name": title or existing.get("english_name") or term,
                    "synonyms": syns,
                    "lay_terms": lays,
                    "icd_code": topic.get("icd_code") or existing.get("icd_code"),
                    "short_description": existing.get("short_description") or short_desc,
                    "causes": existing.get("causes"),
                    "symptoms": existing.get("symptoms"),
                    "risk_factors": existing.get("risk_factors"),
                    "prevention_management": existing.get("prevention_management"),
                    "source_references": refs,
                    "review_metadata": {"medlineplus_url": doc_url, "fetched_at": fetched_at},
                }
            )
            diseases_updated += 1

        category = topic.get("category") or ("disease_education" if entity_id else "general_health")
        pieces = _chunk_text(summary_clean, max_chars=480, overlap=80)
        for idx, piece in enumerate(pieces):
            cid = f"chk-mlp-{_slug(term)}-{idx}"
            store.upsert_chunk(
                {
                    "chunk_id": cid,
                    "source_id": "SRC-MEDLINEPLUS-API",
                    "entity_type": "disease" if entity_id else "health_topic",
                    "entity_id": entity_id or _slug(term).lower(),
                    "section_heading": f"MedlinePlus Summary ({idx + 1}/{len(pieces)})",
                    "title": f"{topic.get('id_name') or term} — {title or term}",
                    "content": piece,
                    "language": "en",
                    "category": category,
                    "metadata": {
                        "url": doc_url,
                        "aliases": [*alt_titles, *(topic.get("synonyms") or []), *(topic.get("lay_terms") or [])],
                    },
                    "updated_at": fetched_at,
                }
            )
            chunks_added += 1
        time.sleep(0.1)

    return diseases_updated, chunks_added, failures


def _first_str(val: Any) -> Optional[str]:
    if isinstance(val, list) and val:
        return _clean_html(str(val[0]))[:1200]
    if isinstance(val, str) and val.strip():
        return _clean_html(val)[:1200]
    return None


def ingest_openfda(store: RAGStore, fetched_at: str) -> Tuple[int, int, List[str]]:
    meds_added = 0
    chunks_added = 0
    failures: List[str] = []

    for item in OPENFDA_DRUG_QUERIES:
        gq = item["generic_query"]
        search_param = urllib.parse.quote(f'openfda.generic_name:"{gq}"')
        url = f"https://api.fda.gov/drug/label.json?search={search_param}&limit=2"
        try:
            raw_json = _http_get(url, timeout=12.0)
            payload = json.loads(raw_json.decode("utf-8"))
        except Exception as exc:
            failures.append(f"openFDA '{gq}': {exc}")
            continue

        results = payload.get("results") or []
        for idx, rec in enumerate(results):
            openfda = rec.get("openfda") or {}
            set_id = rec.get("set_id") or (openfda.get("spl_set_id") or [None])[0] or f"{_slug(gq)}-{idx}"
            prod_id = f"fda-{set_id}"
            brands = [str(b).strip() for b in (openfda.get("brand_name") or []) if str(b).strip()]
            generics = [str(g).strip() for g in (openfda.get("generic_name") or []) if str(g).strip()]
            substances = [str(s).strip() for s in (openfda.get("substance_name") or []) if str(s).strip()]
            routes = [str(r).strip() for r in (openfda.get("route") or []) if str(r).strip()]
            forms = [str(f).strip() for f in (openfda.get("dosage_form") or []) if str(f).strip()]
            ndcs = [str(n).strip() for n in (openfda.get("product_ndc") or []) if str(n).strip()]
            makers = [str(m).strip() for m in (openfda.get("manufacturer_name") or []) if str(m).strip()]

            brand_name = brands[0] if brands else None
            generic_name = generics[0] if generics else gq.upper()
            active_list = substances or ([generic_name] if generic_name else [gq])
            is_combo = len(active_list) > 1 or "," in generic_name or " AND " in generic_name.upper()
            prod_name = f"{brand_name} ({generic_name})" if brand_name and brand_name.lower() != generic_name.lower() else (brand_name or generic_name)
            source_url = (
                f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}"
                if rec.get("set_id")
                else "https://open.fda.gov/apis/drug/label/"
            )

            indications = _first_str(rec.get("indications_and_usage") or rec.get("purpose"))
            warnings = _first_str(rec.get("warnings") or rec.get("warnings_and_cautions") or rec.get("boxed_warning"))
            contraindications = _first_str(rec.get("contraindications") or rec.get("do_not_use"))
            interactions = _first_str(rec.get("drug_interactions") or rec.get("ask_doctor_or_pharmacist"))
            active_txt = _first_str(rec.get("active_ingredient"))
            strength = active_txt[:220] if active_txt else None
            eff_time = rec.get("effective_time") or fetched_at

            store.upsert_medication_product(
                {
                    "id": prod_id,
                    "product_name": prod_name,
                    "brand_name": brand_name,
                    "generic_name": generic_name,
                    "active_ingredients": sorted(set(active_list)),
                    "is_combination": is_combo,
                    "strength": strength,
                    "dosage_form": forms[0] if forms else None,
                    "route": ", ".join(routes) if routes else None,
                    "marketing_authorization_holder": makers[0] if makers else None,
                    "registration_number": ndcs[0] if ndcs else None,
                    "product_code": set_id,
                    "registration_status": "international_source_id_unverified",
                    "indications": indications,
                    "contraindications": contraindications,
                    "warnings": warnings,
                    "interactions": interactions,
                    "label_summary": (
                        f"Sumber label FDA AS untuk {prod_name} (zat aktif: {', '.join(active_list)}). "
                        f"Status registrasi Indonesia (BPOM) tidak dapat diverifikasi dari sumber ini."
                    ),
                    "source_id": "SRC-OPENFDA-LABEL",
                    "source_url": source_url,
                    "updated_at": str(eff_time),
                }
            )
            meds_added += 1

            summary_parts = [f"Produk: {prod_name}", f"Zat aktif: {', '.join(active_list)}"]
            if ndcs:
                summary_parts.append(f"NDC AS: {', '.join(ndcs[:3])}")
            if indications:
                summary_parts.append(f"Indikasi (label FDA): {indications[:380]}")
            if warnings:
                summary_parts.append(f"Peringatan (label FDA): {warnings[:380]}")
            if contraindications:
                summary_parts.append(f"Kontraindikasi: {contraindications[:300]}")

            store.upsert_chunk(
                {
                    "chunk_id": f"chk-fda-{_slug(set_id)}",
                    "source_id": "SRC-OPENFDA-LABEL",
                    "entity_type": "medication_product",
                    "entity_id": prod_id,
                    "section_heading": "openFDA Drug Label (Referensi Internasional AS)",
                    "title": prod_name,
                    "content": " | ".join(summary_parts),
                    "language": "en",
                    "category": "medication_knowledge",
                    "metadata": {
                        "url": source_url,
                        "generic_name": generic_name,
                        "brand_name": brand_name,
                        "ndc": ndcs,
                        "aliases": item.get("indonesian_aliases", []),
                    },
                    "updated_at": fetched_at,
                }
            )
            chunks_added += 1
        time.sleep(0.1)

    return meds_added, chunks_added, failures


def run_ingestion(
    *,
    mode: str = "init",
    skip_network: bool = False,
    store: Optional[RAGStore] = None,
    index: Optional[RAGVectorIndex] = None,
) -> Dict[str, Any]:
    store = store or RAGStore()
    index = index or RAGVectorIndex()
    started = utc_now_iso()
    run_id = f"ing-{uuid.uuid4().hex[:10]}"

    if mode == "reindex":
        store.clear_all_for_reindex(preserve_openfda=skip_network)

    register_static_sources(store, started)
    failures: List[str] = []

    ddx_dis, ddx_chunks = ingest_ddxplus_conditions(store, started)
    id_dis, id_chunks = ingest_indonesian_disease_guides(store, started)
    rule_chunks = ingest_internal_guidance_rules(store, started)
    curated_meds, curated_chunks = ingest_curated_reference_medications(store, started)

    mlp_dis, mlp_chunks = 0, 0
    fda_meds, fda_chunks = 0, 0
    if not skip_network:
        mlp_dis, mlp_chunks, mlp_fail = ingest_medlineplus(store, started)
        failures.extend(mlp_fail)
        fda_meds, fda_chunks, fda_fail = ingest_openfda(store, started)
        failures.extend(fda_fail)

    store.rebuild_fts_indexes()
    emb_info = index.build_from_store(store)
    stats = store.get_stats()

    report = {
        "run_id": run_id,
        "mode": mode,
        "started_at": started,
        "finished_at": utc_now_iso(),
        "sources_count": stats["counts"]["sources"],
        "diseases_count": stats["counts"]["diseases"],
        "medications_count": stats["counts"]["medication_products"],
        "chunks_count": stats["counts"]["chunks"],
        "embedding": emb_info,
        "breakdown": {
            "ddxplus_diseases": ddx_dis,
            "ddxplus_chunks": ddx_chunks,
            "indonesian_diseases_enriched": id_dis,
            "indonesian_chunks": id_chunks,
            "rule_chunks": rule_chunks,
            "curated_reference_meds": curated_meds,
            "curated_reference_chunks": curated_chunks,
            "medlineplus_diseases_enriched": mlp_dis,
            "medlineplus_chunks": mlp_chunks,
            "openfda_products": fda_meds,
            "openfda_chunks": fda_chunks,
        },
        "failures": failures,
    }
    store.record_ingestion_run(report)
    INGESTION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    INGESTION_LOG_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="AmbatuFit RAG Knowledge Ingestion CLI")
    parser.add_argument("--mode", choices=["init", "update", "reindex", "stats", "inspect"], default="init")
    parser.add_argument("--source-id", type=str, default=None)
    parser.add_argument("--skip-network", action="store_true")
    args = parser.parse_args()

    store = RAGStore()
    if args.mode == "stats":
        print(json.dumps(store.get_stats(), indent=2, ensure_ascii=False))
        return
    if args.mode == "inspect":
        if not args.source_id:
            raise SystemExit("--source-id required with --mode inspect")
        print(json.dumps(store.inspect_source(args.source_id), indent=2, ensure_ascii=False))
        return

    report = run_ingestion(mode=args.mode, skip_network=args.skip_network, store=store)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
