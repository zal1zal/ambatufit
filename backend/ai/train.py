import os
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, accuracy_score
from ai.metadata import DDXPLUS_CONDITIONS
from ai.preprocess import DDXPlusFeatureEncoder

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(MODEL_DIR, "model.joblib")
ENCODER_PATH = os.path.join(MODEL_DIR, "encoder.joblib")


def generate_synthetic_ddxplus_dataset(n_samples: int = 1500, random_state: int = 42):
    """
    Generates synthetic training dataset mimicking DDXPlus structured evidence distributions.
    Allows local reproducibility when full multi-GB DDXPlus benchmark is not locally mounted.
    """
    rng = np.random.RandomState(random_state)
    n_classes = len(DDXPLUS_CONDITIONS)
    n_features = len(DDXPlusFeatureEncoder().feature_names)

    X = rng.binomial(n=1, p=0.15, size=(n_samples, n_features)).astype(np.float32)
    # Age normalized
    X[:, 0] = rng.uniform(0.18, 0.75, size=n_samples)
    # Sex one-hot
    sex = rng.choice([0, 1, 2], size=n_samples, p=[0.48, 0.48, 0.04])
    X[:, 1] = (sex == 0).astype(np.float32)
    X[:, 2] = (sex == 1).astype(np.float32)

    # Condition correlation signatures
    # 0: GERD -> nausea (col 16), fatigue
    # 1: URTI -> cough (col 12), persistent fever
    # 2: Tension headache -> headache (col 15)
    # 3: Muscle strain -> joint/muscle pain (col 13)
    # 4: Allergic rhinitis -> cough, allergic reaction
    y = np.zeros(n_samples, dtype=int)
    for i in range(n_samples):
        if X[i, 13] > 0.5:  # joint/muscle
            y[i] = 3
        elif X[i, 15] > 0.5:  # headache
            y[i] = 2
        elif X[i, 12] > 0.5:  # cough
            y[i] = 1
        elif X[i, 16] > 0.5:  # nausea
            y[i] = 0
        else:
            y[i] = rng.choice(n_classes)

    return X, y


def train_model():
    print("Training DDXPlus Multiclass Logistic Regression baseline...")
    encoder = DDXPlusFeatureEncoder()
    X, y = generate_synthetic_ddxplus_dataset(n_samples=2000, random_state=42)

    # Train / Val split (80 / 20)
    split = int(0.8 * len(X))
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    clf = LogisticRegression(
        max_iter=1000,
        solver="lbfgs",
        random_state=42,
    )
    clf.fit(X_train, y_train)

    val_preds = clf.predict(X_val)
    macro_f1 = f1_score(y_val, val_preds, average="macro")
    acc = accuracy_score(y_val, val_preds)

    print(f"Model trained successfully! Validation Accuracy: {acc:.4f}, Macro F1: {macro_f1:.4f}")

    joblib.dump(clf, MODEL_PATH)
    joblib.dump(encoder, ENCODER_PATH)
    print(f"Artifacts saved to {MODEL_PATH} and {ENCODER_PATH}")
    return clf, encoder


if __name__ == "__main__":
    train_model()
