import json
import joblib
import pandas as pd
import numpy as np

MODEL_PATH = "rf_triage_pipeline.joblib"
DATA_PATH = "balanced_data.csv"   

model = joblib.load(MODEL_PATH)
pre = model.named_steps["preprocess"]
cols = list(pre.feature_names_in_)

df = pd.read_csv(DATA_PATH)
X = df[cols].copy()

proba = model.predict_proba(X)
pred = model.predict(X)

classes = list(model.classes_)  

def top_examples_for_class(target_class, k=3):
    idx_class = classes.index(target_class)
    scores = proba[:, idx_class]
    mask = (pred == target_class)
    cand = np.where(mask)[0]
    cand = cand[np.argsort(scores[cand])[::-1]]
    return cand[:k]

def row_to_payload(i):
    r = X.iloc[i].to_dict()
    clean = {}
    for k,v in r.items():
        if pd.isna(v):
            clean[k] = None
        elif isinstance(v, (np.integer,)):
            clean[k] = int(v)
        elif isinstance(v, (np.floating,)):
            clean[k] = float(v)
        else:
            clean[k] = v
    return clean

out = {}
for c in classes:
    ids = top_examples_for_class(c, k=2)
    out[str(c)] = [
        {"proba": float(proba[i, classes.index(c)]), "payload": row_to_payload(i)}
        for i in ids
    ]

print(json.dumps(out, indent=2, ensure_ascii=False))
