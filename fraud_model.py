import numpy as np
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.tree import DecisionTreeClassifier

class FraudModel:
    """Demo model trained on generated examples; replace with a consented, labelled dataset."""
    def __init__(self):
        rng = np.random.default_rng(42)
        n = 700
        X = np.column_stack([
            rng.integers(0, 8, n),          # failed attempts
            rng.uniform(0.35, 1.0, n),      # OCR confidence
            rng.integers(0, 2, n),          # duplicate indicator
            rng.integers(0, 4, n),          # device changes
            rng.integers(0, 2, n),          # document mismatch
        ])
        y = ((X[:,0] >= 4) | (X[:,2] == 1) | (X[:,4] == 1) | ((X[:,1] < .58) & (X[:,3] >= 2))).astype(int)
        self.rf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
        self.dt = DecisionTreeClassifier(max_depth=5, random_state=42, class_weight="balanced")
        self.iso = IsolationForest(contamination=.12, random_state=42)
        self.rf.fit(X, y); self.dt.fit(X, y); self.iso.fit(X)

    def predict(self, failed_attempts=0, ocr_confidence=.95, duplicate=0, device_changes=0, mismatch=0):
        row = np.array([[failed_attempts, ocr_confidence, duplicate, device_changes, mismatch]], dtype=float)
        probability = float(self.rf.predict_proba(row)[0][1])
        anomaly = self.iso.predict(row)[0] == -1
        score = int(min(99, max(1, round(probability * 85 + (14 if anomaly else 0)))))
        label = "High Risk" if score >= 70 else ("Medium Risk" if score >= 40 else "Low Risk")
        reasons = []
        if duplicate: reasons.append("Possible duplicate identity")
        if mismatch: reasons.append("Document consistency needs review")
        if failed_attempts >= 4: reasons.append("Multiple failed verification attempts")
        if device_changes >= 2: reasons.append("Unusual device changes")
        if ocr_confidence < .58: reasons.append("Low OCR confidence")
        if not reasons and anomaly: reasons.append("Unusual feature combination")
        if not reasons: reasons.append("No major risk indicators detected")
        return {"score": score, "level": label, "prediction": "Suspicious" if score >= 40 else "Normal",
                "reasons": reasons, "decision_tree": "Suspicious" if int(self.dt.predict(row)[0]) else "Normal"}
