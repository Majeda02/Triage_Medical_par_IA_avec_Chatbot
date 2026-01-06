import joblib
import pandas as pd
from collections import Counter

MODEL_PATH = "rf_triage_pipeline.joblib"
DATA_PATH = "balanced_data.csv"   

model = joblib.load(MODEL_PATH)

pre = model.named_steps["preprocess"]
EXPECTED_COLS = list(pre.feature_names_in_)

df = pd.read_csv(DATA_PATH)

X = df[EXPECTED_COLS].copy()

pred = model.predict(X)

print("classes_:", getattr(model, "classes_", None))
print("Expected cols:", EXPECTED_COLS)
print("Prediction counts:", Counter(pred))
