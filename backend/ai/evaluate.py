"""Evaluate trained DDXPlus Logistic Regression bundle on the untouched official test split."""
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from ai.metadata import AI_DIR, BUNDLE_PATH, METADATA_PATH, get_data_dir
from ai.train import iter_zip_csv_rows, top_k_accuracy

EVAL_METRICS_PATH = AI_DIR / "evaluation_metrics.json"
EVAL_REPORT_PATH = AI_DIR / "evaluation_report.txt"


def evaluate_model(data_dir: Path | str | None = None, bundle_path: Path | None = None):
    artifact_path = Path(bundle_path or BUNDLE_PATH)
    if not artifact_path.exists():
        raise FileNotFoundError(f"Model bundle not found at {artifact_path}. Run `python -m ai.train` first.")

    bundle = joblib.load(artifact_path)
    clf = bundle["estimator"]
    encoder = bundle["encoder"]
    label_names = bundle["label_names"]
    label_to_idx = {name: i for i, name in enumerate(label_names)}

    root = get_data_dir(data_dir)
    t0 = time.perf_counter()
    X_test, y_test, test_stats = encoder.transform_csv_split(
        iter_zip_csv_rows(root / "release_test_patients.zip"), label_to_idx
    )
    print(f"Loaded untouched test split: {X_test.shape} in {time.perf_counter() - t0:.1f}s", flush=True)

    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)

    macro_f1 = float(f1_score(y_test, y_pred, average="macro"))
    weighted_f1 = float(f1_score(y_test, y_pred, average="weighted"))
    top1 = float(accuracy_score(y_test, y_pred))
    top3 = top_k_accuracy(y_test, y_prob, 3)
    top5 = top_k_accuracy(y_test, y_prob, 5)
    cm = confusion_matrix(y_test, y_pred, labels=list(range(len(label_names))))

    report_dict = classification_report(
        y_test, y_pred, target_names=label_names, digits=4, output_dict=True, zero_division=0
    )
    report_text = classification_report(
        y_test, y_pred, target_names=label_names, digits=4, zero_division=0
    )

    # Identify minority / lowest-F1 classes and top off-diagonal confusions
    per_class = [
        {
            "condition": name,
            "f1_score": round(float(report_dict[name]["f1-score"]), 4),
            "precision": round(float(report_dict[name]["precision"]), 4),
            "recall": round(float(report_dict[name]["recall"]), 4),
            "support": int(report_dict[name]["support"]),
        }
        for name in label_names
    ]
    lowest_f1 = sorted(per_class, key=lambda r: r["f1_score"])[:5]
    minority_classes = sorted(per_class, key=lambda r: r["support"])[:5]

    cm_off = cm.copy()
    np.fill_diagonal(cm_off, 0)
    flat_top = np.argsort(cm_off.ravel())[-10:][::-1]
    top_confusions = []
    for idx in flat_top:
        true_i, pred_i = divmod(int(idx), len(label_names))
        count = int(cm_off[true_i, pred_i])
        if count > 0:
            top_confusions.append(
                {
                    "true_condition": label_names[true_i],
                    "predicted_condition": label_names[pred_i],
                    "count": count,
                }
            )

    evaluated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    metrics = {
        "model_version": bundle["model_version"],
        "evaluated_at": evaluated_at,
        "test_split": "release_test_patients.zip (untouched hold-out split)",
        "test_samples": test_stats["rows"],
        "unknown_tokens": test_stats["unknown_tokens"],
        "n_classes": len(label_names),
        "macro_f1": round(macro_f1, 6),
        "weighted_f1": round(weighted_f1, 6),
        "top_k_accuracy": {
            "top_1": round(top1, 6),
            "top_3": round(top3, 6),
            "top_5": round(top5, 6),
        },
        "lowest_f1_classes": lowest_f1,
        "smallest_support_classes": minority_classes,
        "top_confusion_pairs": top_confusions,
        "per_class": per_class,
        "confusion_matrix_labels": label_names,
        "confusion_matrix": cm.tolist(),
        "clinical_validity_notice": (
            "Evaluated on synthetic DDXPlus hold-out split. Metrics measure synthetic benchmark "
            "performance only and do not establish clinical safety or validity on real patients."
        ),
    }
    EVAL_METRICS_PATH.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    # Sync test summary back into model_metadata.json
    if METADATA_PATH.exists():
        meta = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        meta["dataset"]["test_rows"] = test_stats["rows"]
        meta["test_evaluation"] = {
            "evaluated_at": evaluated_at,
            "test_samples": test_stats["rows"],
            "macro_f1": metrics["macro_f1"],
            "weighted_f1": metrics["weighted_f1"],
            "top_k_accuracy": metrics["top_k_accuracy"],
        }
        METADATA_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    confusion_lines = "\n".join(
        f"  - {c['true_condition']} -> {c['predicted_condition']}: {c['count']:,}"
        for c in top_confusions
    )
    minority_lines = "\n".join(
        f"  - {c['condition']} (support={c['support']:,}): F1={c['f1_score']:.4f}, P={c['precision']:.4f}, R={c['recall']:.4f}"
        for c in minority_classes
    )
    lowest_lines = "\n".join(
        f"  - {c['condition']} (support={c['support']:,}): F1={c['f1_score']:.4f}, P={c['precision']:.4f}, R={c['recall']:.4f}"
        for c in lowest_f1
    )

    summary_txt = (
        "====================================================================\n"
        "AmbatuFit Official DDXPlus ML Evaluation Report\n"
        "====================================================================\n"
        f"Model Version:      {bundle['model_version']}\n"
        "Algorithm:          Multiclass Logistic Regression (scikit-learn)\n"
        "Dataset Source:     Official DDXPlus English (DOI: 10.6084/m9.figshare.22687585.v2, CC BY 4.0)\n"
        "Evaluation Split:   release_test_patients.zip (untouched test split)\n"
        f"Total Test Samples: {test_stats['rows']:,}\n"
        f"Total Classes:      {len(label_names)}\n"
        f"Macro F1-Score:     {macro_f1:.4f}\n"
        f"Weighted F1-Score:  {weighted_f1:.4f}\n"
        f"Top-1 Accuracy:     {top1:.4f} (k=1)\n"
        f"Top-3 Accuracy:     {top3:.4f} (k=3)\n"
        f"Top-5 Accuracy:     {top5:.4f} (k=5)\n\n"
        "5 Smallest Support (Minority) Classes:\n"
        f"{minority_lines}\n\n"
        "5 Lowest F1 Classes:\n"
        f"{lowest_lines}\n\n"
        "Top 10 Confusion Pairs (True -> Predicted):\n"
        f"{confusion_lines}\n\n"
        "Full Per-Class Classification Report:\n"
        f"{report_text}\n"
        "Confusion Matrix (49x49): saved in backend/ai/evaluation_metrics.json\n"
        "====================================================================\n"
        "Important: DDXPlus is a synthetic dataset. These metrics measure benchmark\n"
        "performance on simulated patients and do NOT prove clinical validity.\n"
        "Outputs are internal support signals only — never clinical diagnoses,\n"
        "red-flag overrides, or medication recommendations.\n"
    )
    EVAL_REPORT_PATH.write_text(summary_txt, encoding="utf-8")
    print(summary_txt, flush=True)
    return metrics


if __name__ == "__main__":
    evaluate_model()
