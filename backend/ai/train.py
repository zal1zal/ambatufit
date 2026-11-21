"""Train official DDXPlus Multiclass Logistic Regression model using train/validate splits only."""
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import platform
import time
import zipfile

import joblib
import numpy as np
import scipy
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

from ai.metadata import (
    ARTIFACTS_DIR,
    BUNDLE_PATH,
    DATASET_SOURCE,
    METADATA_PATH,
    export_core_evidence_snapshot,
    get_data_dir,
    load_ddxplus_conditions,
    load_ddxplus_evidences,
)
from ai.preprocess import DDXPlusFeatureEncoder

MODEL_VERSION = "ddxplus-lr-en-v2.0"


def iter_zip_csv_rows(zip_path: Path):
    if not zip_path.exists():
        raise FileNotFoundError(
            f"Official DDXPlus split not found: {zip_path}. Run `python -m ai.download_ddxplus`."
        )
    with zipfile.ZipFile(zip_path) as zf:
        member = zf.namelist()[0]
        with zf.open(member) as raw:
            yield from csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"))


def top_k_accuracy(y_true: np.ndarray, y_prob: np.ndarray, k: int) -> float:
    k_eff = min(k, y_prob.shape[1])
    top_k = np.argpartition(y_prob, -k_eff, axis=1)[:, -k_eff:]
    return float(np.mean(np.any(top_k == y_true[:, None], axis=1)))


def train_model(
    data_dir: Path | str | None = None,
    candidates: tuple[tuple[float, str | None], ...] = ((1.0, None), (1.0, "balanced")),
    max_iter: int = 200,
    tol: float = 1e-4,
    random_state: int = 42,
):
    root = get_data_dir(data_dir)
    evidences = load_ddxplus_evidences(root)
    conditions = load_ddxplus_conditions(root)
    label_names = sorted(conditions.keys())
    label_to_idx = {name: i for i, name in enumerate(label_names)}

    # Keep STB core evidence metadata strictly synchronized with official DDXPlus release
    export_core_evidence_snapshot(root)

    encoder = DDXPlusFeatureEncoder(evidences)
    t0 = time.perf_counter()
    print(f"Loading official DDXPlus train split from {root}...", flush=True)
    X_train, y_train, train_stats = encoder.transform_csv_split(
        iter_zip_csv_rows(root / "release_train_patients.zip"), label_to_idx
    )
    print(
        f"Loaded train: {X_train.shape} (nnz={X_train.nnz:,}, unknown_tokens={train_stats['unknown_tokens']}) "
        f"in {time.perf_counter() - t0:.1f}s",
        flush=True,
    )

    t1 = time.perf_counter()
    X_val, y_val, val_stats = encoder.transform_csv_split(
        iter_zip_csv_rows(root / "release_validate_patients.zip"), label_to_idx
    )
    print(
        f"Loaded validate: {X_val.shape} (nnz={X_val.nnz:,}, unknown_tokens={val_stats['unknown_tokens']}) "
        f"in {time.perf_counter() - t1:.1f}s",
        flush=True,
    )

    # Validation-only model selection (test set is NEVER touched during training/tuning)
    validation_trials = []
    best_model = None
    best_score = -1.0
    best_cfg = candidates[0]

    for c_val, cw in candidates:
        ts = time.perf_counter()
        clf = LogisticRegression(
            C=c_val,
            class_weight=cw,
            solver="lbfgs",
            max_iter=max_iter,
            tol=tol,
            random_state=random_state,
        )
        clf.fit(X_train, y_train)
        val_pred = clf.predict(X_val)
        val_prob = clf.predict_proba(X_val)
        trial = {
            "C": c_val,
            "class_weight": cw,
            "val_macro_f1": round(float(f1_score(y_val, val_pred, average="macro")), 6),
            "val_top1_accuracy": round(float(accuracy_score(y_val, val_pred)), 6),
            "val_top3_accuracy": round(top_k_accuracy(y_val, val_prob, 3), 6),
            "val_top5_accuracy": round(top_k_accuracy(y_val, val_prob, 5), 6),
            "n_iter": int(np.max(clf.n_iter_)),
            "fit_seconds": round(time.perf_counter() - ts, 2),
        }
        validation_trials.append(trial)
        print(f"Validation C={c_val} class_weight={cw}: {trial}", flush=True)
        if trial["val_macro_f1"] > best_score:
            best_score = trial["val_macro_f1"]
            best_model = clf
            best_cfg = (c_val, cw)

    manifest_path = root / "manifest.json"
    dataset_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    condition_metadata = {
        name: {
            "icd10_id": meta.get("icd10-id"),
            "severity": meta.get("severity"),
        }
        for name, meta in conditions.items()
    }
    trained_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    metadata = {
        "model_version": MODEL_VERSION,
        "algorithm": "Multiclass LogisticRegression (scikit-learn)",
        "trained_at": trained_at,
        "schema_hash": encoder.schema_hash,
        "n_features": encoder.n_features,
        "n_classes": len(label_names),
        "dataset": {
            **DATASET_SOURCE,
            "train_rows": train_stats["rows"],
            "validate_rows": val_stats["rows"],
            "files_md5": {k: v.get("md5") for k, v in (dataset_manifest.get("files") or {}).items()},
        },
        "training_params": {
            "selected_C": best_cfg[0],
            "selected_class_weight": best_cfg[1],
            "solver": "lbfgs",
            "max_iter": max_iter,
            "tol": tol,
            "random_state": random_state,
            "validation_trials": validation_trials,
        },
        "environment": {
            "python_version": platform.python_version(),
            "scikit_learn_version": sklearn.__version__,
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
            "joblib_version": joblib.__version__,
        },
        "clinical_validity_notice": (
            "Trained on synthetic DDXPlus benchmark data. Performance does NOT establish clinical "
            "validity on real patients and model outputs are never clinical diagnoses or prescriptions."
        ),
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model_version": MODEL_VERSION,
        "schema_hash": encoder.schema_hash,
        "estimator": best_model,
        "encoder": encoder,
        "label_names": label_names,
        "condition_metadata": condition_metadata,
        "metadata": metadata,
    }
    joblib.dump(bundle, BUNDLE_PATH, compress=3)
    METADATA_PATH.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    # Remove obsolete prototype artifacts if present
    for legacy in (ARTIFACTS_DIR.parent / "model.joblib", ARTIFACTS_DIR.parent / "encoder.joblib"):
        legacy.unlink(missing_ok=True)

    print(f"Saved model bundle to {BUNDLE_PATH} ({BUNDLE_PATH.stat().st_size:,} bytes)", flush=True)
    print(f"Saved metadata to {METADATA_PATH}", flush=True)
    return bundle


if __name__ == "__main__":
    train_model()
