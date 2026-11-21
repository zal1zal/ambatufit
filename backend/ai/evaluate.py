import os
import joblib
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from ai.metadata import DDXPLUS_CONDITIONS
from ai.preprocess import DDXPlusFeatureEncoder
from ai.train import generate_synthetic_ddxplus_dataset, MODEL_PATH, ENCODER_PATH


def evaluate_model():
    if not os.path.exists(MODEL_PATH) or not os.path.exists(ENCODER_PATH):
        raise FileNotFoundError("Model artifacts not found. Run train.py first.")

    clf = joblib.load(MODEL_PATH)
    encoder = joblib.load(ENCODER_PATH)

    # Independent test dataset
    X_test, y_test = generate_synthetic_ddxplus_dataset(n_samples=500, random_state=999)
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)

    # Top-k accuracy (Top-3)
    top_3_correct = 0
    for i in range(len(y_test)):
        top_3_indices = np.argsort(y_prob[i])[-3:]
        if y_test[i] in top_3_indices:
            top_3_correct += 1
    top_3_acc = top_3_correct / len(y_test)

    acc = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average="macro")
    cm = confusion_matrix(y_test, y_pred)

    class_names = [c["name"] for c in DDXPLUS_CONDITIONS]

    report = f"""
======================================================
AmbatuFit ML Evaluation Report (DDXPlus Baseline)
======================================================
Model Architecture: Multiclass Logistic Regression
Total Test Samples: {len(y_test)}
Accuracy (Top-1):   {acc:.4f}
Top-3 Accuracy:     {top_3_acc:.4f}
Macro F1-Score:     {macro_f1:.4f}

Classification Report:
{classification_report(y_test, y_pred, target_names=class_names, digits=4)}

Confusion Matrix:
{cm}
======================================================
Important: This evaluation measures performance on synthetic benchmark data
and does not establish clinical safety or validity on real patients.
"""
    print(report)
    with open(os.path.join(os.path.dirname(MODEL_PATH), "evaluation_report.txt"), "w", encoding="utf-8") as f:
        f.write(report)
    return {
        "accuracy": acc,
        "top_3_accuracy": top_3_acc,
        "macro_f1": macro_f1,
    }


if __name__ == "__main__":
    evaluate_model()

