# AmbatuFit Machine Learning Service (DDXPlus Baseline)

## Arsitektur & Desain
Layanan inferensi AI ini berjalan **di luar STB** (pada laptop pengembang atau VM server terpisah) untuk menjaga beban CPU dan memori STB agar tidak mengalami *hang* atau *out-of-memory*, sesuai batasan pada Tugas Besar TST (Slide 23).

### Karakteristik Model:
- **Metode**: Supervised Machine Learning menggunakan algoritma Multiclass Logistic Regression (`scikit-learn`).
- **Dataset Acuan**: DDXPlus (Mila / Université de Montréal), dataset medis berisikan keluhan, bukti (*evidences*), dan kondisi patologis.
- **Fitur Masukan**: Umur ternormalisasi, jenis kelamin teknis model (`M`, `F`, `unknown`), serta 14 fitur gejala terstruktur dari katalog bukti.
- **Keluaran**: Pengelompokan pola keluhan internal untuk menyusun ringkasan informatif. Model **tidak pernah mengeluarkan diagnosis klinis langsung**.

### Evaluasi Model:
Evaluasi dilakukan dengan pemisahan data independen menggunakan metrik:
- **Macro F1-Score**
- **Top-1 & Top-3 Accuracy**
- **Confusion Matrix**

Hasil evaluasi disimpan pada `evaluation_report.txt`.

### Menjalankan Layanan AI:
```bash
# 1. Melatih model baseline
python -m ai.train

# 2. Mengevaluasi metrik model
python -m ai.evaluate

# 3. Menjalankan server inferensi (port 8100)
python -m uvicorn ai.server:app --host 0.0.0.0 --port 8100
```

