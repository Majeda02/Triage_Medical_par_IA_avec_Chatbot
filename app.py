import mysql.connector
from mysql.connector import Error
from flask import Flask, request, jsonify, send_from_directory
from flask_restful import Api
from flask_cors import CORS
import json
import os
import traceback
import numbers
import csv
from io import StringIO
from flask import Response


import joblib
import pandas as pd

from package import patient


# =========================================================
# DB imports
# =========================================================
DB_ENABLED = True
try:
    from package.patient import Patients, Patient
    from package.doctor import Doctors, Doctor
    from package.appointment import Appointments, Appointment
    from package.common import Common
    from package.debug import DebugDB
except Exception as e:
    DB_ENABLED = False
    print("[WARN] DB modules not loaded. Running ML + static only.")
    print("       Details:", str(e))


# ============================
# Load config
# ============================
CONFIG_PATH = "config.json"
config = {}
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

HOST = config.get("host", "127.0.0.1")
PORT = int(config.get("port", 5000))

def db_connect():
     db_cfg = config.get("mysql", {}) 
     return mysql.connector.connect(
        host=db_cfg.get("host", "127.0.0.1"),
        user=db_cfg.get("user", "root"),
        password=db_cfg.get("password", ""),
        database=db_cfg.get("database", "hospital_db"),
        port=int(db_cfg.get("port", 3306))
       )
# ============================
# Flask app (static in /static)
# ============================
app = Flask(__name__, static_folder="static", static_url_path="")
api = Api(app)
CORS(app)


# ============================
# REST resources (DB)
# ============================
if DB_ENABLED:
    api.add_resource(Patients, "/api/patient")
    api.add_resource(Patient, "/api/patient/<int:id>")

    api.add_resource(Doctors, "/api/doctor")
    api.add_resource(Doctor, "/api/doctor/<int:id>")

    api.add_resource(Appointments, "/api/appointment")
    api.add_resource(Appointment, "/api/appointment/<int:id>")

    api.add_resource(Common, "/api/common")
    api.add_resource(DebugDB, "/api/debug/db")


# ============================
# ML model
# ============================
MODEL_PATH = "rf_triage_pipeline.joblib"
model = None
model_load_error = None
EXPECTED_COLS = None


ID_TO_LABEL = {
    0: "Emergent",
    1: "Semi-urgent",
    2: "Urgent",
}


def detect_expected_cols(m):
    """Detect raw input columns expected by the sklearn pipeline."""
    try:
        if hasattr(m, "named_steps") and "preprocess" in m.named_steps:
            p = m.named_steps["preprocess"]
            if hasattr(p, "feature_names_in_"):
                return list(p.feature_names_in_)
    except Exception:
        pass

    try:
        if hasattr(m, "feature_names_in_"):
            return list(m.feature_names_in_)
    except Exception:
        pass

    return None


def load_model():
    global model, model_load_error, EXPECTED_COLS
    try:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

        model = joblib.load(MODEL_PATH)
        model_load_error = None
        EXPECTED_COLS = detect_expected_cols(model)

        print(f"[OK] Model loaded: {MODEL_PATH}")
        print("[DEBUG] model.classes_ =", getattr(model, "classes_", None))
        print(f"[OK] EXPECTED_COLS detected? {EXPECTED_COLS is not None}")
        if EXPECTED_COLS:
            print(f"[OK] EXPECTED_COLS count = {len(EXPECTED_COLS)}")

    except Exception as e:
        model = None
        EXPECTED_COLS = None
        model_load_error = str(e)
        print("[ERROR] Could not load model:")
        print(traceback.format_exc())


load_model()

def insert_analysis(pat_id, label, pred, payload, proba_map, input_used):
    if not DB_ENABLED:
        return

    try:
        if pat_id in ["", None, "null", "None"]:
            pat_id = None
        elif isinstance(pat_id, str) and pat_id.isdigit():
            pat_id = int(pat_id)
    except Exception:
        pat_id = None

    if proba_map is None:
        proba_map = {}

    payload_s = json.dumps(payload, default=str)
    proba_s = json.dumps(proba_map, default=str)
    input_s = json.dumps(input_used, default=str)

    try:
        conn = db_connect()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO triage_analysis (pat_id, label, pred, payload_json, proba_json, input_used_json)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (pat_id, label, str(pred), payload_s, proba_s, input_s))

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print("[WARN] insert_analysis failed:", str(e))




# ============================
# Helpers
# ============================
def to_bool01(v):
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, str):
        t = v.strip().lower()
        if t in ["yes", "y", "true", "1"]:
            return 1
        if t in ["no", "n", "false", "0"]:
            return 0
    if isinstance(v, (int, float)):
        return 1 if float(v) != 0 else 0
    return 0


def to_float_or_none(x):
    if x is None or x == "":
        return None
    try:
        return float(x)
    except Exception:
        return None


def parse_bp_text(bp_str):
    """Accepts '120/80' => (120.0, 80.0)"""
    if not isinstance(bp_str, str) or "/" not in bp_str:
        return None, None
    a, b = bp_str.split("/", 1)
    try:
        return float(a.strip()), float(b.strip())
    except Exception:
        return None, None


def label_from_pred(pred):
    """Return a human label from pred respecting your encoding."""
    if isinstance(pred, str):
        return pred

    if isinstance(pred, numbers.Integral):
        return ID_TO_LABEL.get(int(pred), str(int(pred)))

    return str(pred)


def build_defaults_row(expected_cols):
    """
    Build defaults that do NOT break categorical columns.
    - start with None
    - set boolean-like columns to "No" (strings) if they are in dataset as Yes/No
    - set pain to "Unknown" if present
    """
    row = {c: None for c in expected_cols}

    for c in expected_cols:
        if c.startswith("is_patient_suffer_"):
            row[c] = "No"

    for b in ["is_arrival_ambulance", "is_patient_seen_before_72h", "patient_alchol_level"]:
        if b in row and row[b] is None:
            row[b] = "No"

    if "patient_pain_category" in row and row["patient_pain_category"] is None:
        row["patient_pain_category"] = "Unknown"

    return row


# ============================
# Static pages
# ============================
@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/chatbot")
@app.get("/chatbot.html")
def chatbot_page():
    return send_from_directory("static", "chatbot.html")


@app.get("/doctor")
@app.get("/doctor.html")
def doctor_page():
    return send_from_directory("static", "doctor.html")


@app.get("/patient")
@app.get("/patient.html")
def patient_page():
    return send_from_directory("static", "patient.html")


# ============================
# Health check
# ============================
@app.get("/api/triage/predict")
def triage_predict_get():
    return jsonify({
        "ok": True,
        "message": "API is working. Use POST with JSON to get prediction.",
        "model_loaded": model is not None,
        "model_error": model_load_error,
        "expected_cols_loaded": EXPECTED_COLS is not None,
        "expected_cols_count": len(EXPECTED_COLS) if EXPECTED_COLS else 0,
        "classes": [str(c) for c in getattr(model, "classes_", [])] if model is not None else None,
        "units": {"temperature": "Fahrenheit"}
    })


# ============================
# Schema endpoint (expected_cols + categories)
# ============================
@app.get("/api/triage/schema")
def triage_schema():
    if model is None:
        return jsonify({"error": "MODEL_NOT_LOADED", "detail": model_load_error}), 500
    if not EXPECTED_COLS:
        return jsonify({"error": "EXPECTED_COLS_NOT_FOUND"}), 500

    schema = {
        "expected_cols": EXPECTED_COLS,
        "classes": [str(c) for c in getattr(model, "classes_", [])],
        "id_to_label": ID_TO_LABEL,  
    }

    try:
        if hasattr(model, "named_steps") and "preprocess" in model.named_steps:
            pre = model.named_steps["preprocess"]
            cats = {}
            for name, trans, cols in getattr(pre, "transformers_", []):
                if hasattr(trans, "categories_"):
                    for c, values in zip(cols, trans.categories_):
                        cats[c] = [str(v) for v in values.tolist()]
            if cats:
                schema["categories"] = cats
    except Exception:
        pass

    return jsonify(schema)



# ============================
# Predict endpoint
# ============================
@app.post("/api/triage/predict")
def triage_predict():
    try:
        payload = request.get_json(force=True) or {}

        if model is None:
            return jsonify({"error": "MODEL_NOT_LOADED", "detail": model_load_error}), 500
        if not EXPECTED_COLS:
            return jsonify({
                "error": "EXPECTED_COLS_NOT_FOUND",
                "detail": "Could not detect training columns from pipeline. Provide EXPECTED_COLS manually."
            }), 500

        row = build_defaults_row(EXPECTED_COLS)
        for c in EXPECTED_COLS:
            if c in payload:
                row[c] = payload[c]

        if "age" in payload and "patient_age" in row:
            row["patient_age"] = to_float_or_none(payload.get("age"))

        if "sex" in payload and "patient_sexe" in row:
            row["patient_sexe"] = payload.get("sex")

        if "heartRate" in payload and "heart_rate_signal" in row:
            row["heart_rate_signal"] = to_float_or_none(payload.get("heartRate"))

        if "temperature" in payload and "temperature_signal" in row:
            row["temperature_signal"] = to_float_or_none(payload.get("temperature"))

        if "respiratoryRate" in payload and "respiratory_rate_signal" in row:
            row["respiratory_rate_signal"] = to_float_or_none(payload.get("respiratoryRate"))

        if "systolicBP" in payload and "blood_pressure_systolic_signal" in row:
            row["blood_pressure_systolic_signal"] = to_float_or_none(payload.get("systolicBP"))

        if "diastolicBP" in payload and "blood_pressure_diastolic_signal" in row:
            row["blood_pressure_diastolic_signal"] = to_float_or_none(payload.get("diastolicBP"))

        if payload.get("bloodPressure"):
            s, d = parse_bp_text(payload.get("bloodPressure"))
            if "blood_pressure_systolic_signal" in row and row.get("blood_pressure_systolic_signal") in [None, ""]:
                row["blood_pressure_systolic_signal"] = s
            if "blood_pressure_diastolic_signal" in row and row.get("blood_pressure_diastolic_signal") in [None, ""]:
                row["blood_pressure_diastolic_signal"] = d

        if "diabetes" in payload and "is_patient_suffer_diabet_L0" in row:
            row["is_patient_suffer_diabet_L0"] = "Yes" if to_bool01(payload.get("diabetes")) == 1 else "No"
        if "heartFailure" in payload and "is_patient_suffer_congestive_heart_failure" in row:
            row["is_patient_suffer_congestive_heart_failure"] = "Yes" if to_bool01(payload.get("heartFailure")) == 1 else "No"
        if "renalInsufficiency" in payload and "is_patient_suffer_renal_insufficiency" in row:
            row["is_patient_suffer_renal_insufficiency"] = "Yes" if to_bool01(payload.get("renalInsufficiency")) == 1 else "No"

        # ==========================================================
        # VALIDATION (Temperature in Fahrenheit)
        # ==========================================================
        temp = row.get("temperature_signal", None)
        temp_val = to_float_or_none(temp)
        if temp_val is not None and (temp_val < 85 or temp_val > 110):
            return jsonify({
                "error": "INVALID_TEMPERATURE_UNIT",
                "detail": "Temperature must be in Fahrenheit (typical 95–105). You likely entered Celsius by mistake.",
                "received_temperature": temp_val
            }), 400

        numeric_cols = {
            "heart_rate_signal",
            "temperature_signal",
            "respiratory_rate_signal",
            "blood_pressure_systolic_signal",
            "blood_pressure_diastolic_signal",
            "pulse_oximetry_signal",
            "patient_age",
            "ambulance_time",
            "year_visit",
        }
        for c in numeric_cols:
            if c in row:
                row[c] = to_float_or_none(row[c])

        X = pd.DataFrame([row], columns=EXPECTED_COLS)

        pred = model.predict(X)[0]
        label = label_from_pred(pred)

        proba_map = None
        if hasattr(model, "predict_proba"):
            try:
                p = model.predict_proba(X)[0]
                classes = [str(c) for c in getattr(model, "classes_", [])]
                proba_map = {classes[i]: float(p[i]) for i in range(len(classes))}
            except Exception:
                proba_map = None

        input_used = {k: row[k] for k in EXPECTED_COLS if row[k] not in [None, ""]}

        pat_id = payload.get("pat_id")

        full_row = {k: row.get(k) for k in EXPECTED_COLS}

        
        insert_analysis(
            pat_id=pat_id,
            label=label,
            pred=pred,
            payload=full_row,
            proba_map=proba_map,
            input_used=input_used
         )



        return jsonify({
            "label": label,  
            "pred": int(pred) if isinstance(pred, numbers.Integral) else str(pred),
            "proba_map": proba_map,
            "input_used": input_used,
            "classes": [str(c) for c in getattr(model, "classes_", [])],
            "id_to_label": ID_TO_LABEL,
            "units": {"temperature": "Fahrenheit"},
        })

    except Exception:
        print("[ERROR] /api/triage/predict failed:")
        print(traceback.format_exc())
        return jsonify({
            "error": "PREDICT_FAILED",
            "detail": traceback.format_exc()
        }), 500

@app.get("/api/patient/<int:pat_id>/triage-analyses")
def patient_triage_analyses(pat_id):
    if not DB_ENABLED:
        return jsonify({"error": "DB_DISABLED"}), 500

    try:
        conn = db_connect()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT *
            FROM triage_analysis
            WHERE pat_id = %s
            ORDER BY created_at DESC
        """, (pat_id,))

        rows = cur.fetchall()
        cur.close()
        conn.close()

        for r in rows:
            if "created_at" in r and r["created_at"] is not None:
                r["created_at"] = str(r["created_at"])

        return jsonify(rows), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.get("/api/triage/analysis-counts")
def triage_analysis_counts():
    """
    Returns counts of analyses per patient.
    Query: /api/triage/analysis-counts?ids=1,2,3
    Response: { "1": 2, "2": 0, "3": 5 }
    """
    if not DB_ENABLED:
        return jsonify({"error": "DB_DISABLED"}), 500

    ids_param = request.args.get("ids", "").strip()
    if not ids_param:
        return jsonify({})

    ids = []
    for part in ids_param.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))

    if not ids:
        return jsonify({})

    try:
        conn = db_connect()
        cur = conn.cursor(dictionary=True)

        placeholders = ",".join(["%s"] * len(ids))
        cur.execute(f"""
            SELECT pat_id, COUNT(*) AS cnt
            FROM triage_analysis
            WHERE pat_id IN ({placeholders})
            GROUP BY pat_id
        """, tuple(ids))

        rows = cur.fetchall()
        cur.close()
        conn.close()

        out = {str(i): 0 for i in ids}
        for r in rows:
            out[str(r["pat_id"])] = int(r["cnt"])

        return jsonify(out)

    except Exception as e:
        print("[ERROR] analysis-counts failed:", str(e))
        return jsonify({"error": "COUNTS_FAILED", "detail": str(e)}), 500

@app.get("/api/patient/<int:pat_id>/triage-export.csv")
def export_patient_triage_csv(pat_id):
    if not DB_ENABLED:
        return jsonify({"error": "DB_DISABLED"}), 500

    def to_dict(x):
        if x is None:
            return {}
        if isinstance(x, dict):
            return x
        if isinstance(x, (bytes, bytearray)):
            try:
                x = x.decode("utf-8", errors="ignore")
            except Exception:
                return {}
        if isinstance(x, str):
            x = x.strip()
            if not x:
                return {}
            try:
                return json.loads(x)
            except Exception:
                return {}
        return {}

    try:
        conn = db_connect()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT pat_id, pat_first_name, pat_last_name, pat_insurance_no, pat_address, pat_ph_no
            FROM patient
            WHERE pat_id = %s
        """, (pat_id,))
        patient = cur.fetchone()
        if not patient:
            cur.close()
            conn.close()
            return jsonify({"error": "PATIENT_NOT_FOUND"}), 404

        cur.execute("""
            SELECT pat_id, created_at, label, payload_json
            FROM triage_analysis
            WHERE pat_id = %s
            ORDER BY created_at DESC
        """, (pat_id,))
        analyses = cur.fetchall()

        cur.close()
        conn.close()

        patient_cols = ["pat_first_name","pat_last_name","pat_insurance_no","pat_ph_no","pat_address"]
        base_cols = ["created_at","label"]

        REQUIRED_FEATURES = [
            "month_visit","day_visit","year_visit",
            "is_arrival_ambulance","ambulance_time",
            "patient_age","patient_sexe","patient_race",
            "heart_rate_signal","temperature_signal","respiratory_rate_signal",
            "blood_pressure_systolic_signal","blood_pressure_diastolic_signal",
            "pulse_oximetry_signal",
            "patient_pain_category",
            "is_patient_seen_before_72h",
            "patient_alchol_level",
            "is_patient_suffer_alzheimar",
            "is_patient_suffer_cancer",
            "is_patient_suffer_cerebrovascular",
            "is_patient_suffer_chronic_kidney",
            "is_patient_suffer_chronic_obstructive_pulmonary",
            "is_patient_suffer_congestive_heart_failure",
            "is_patient_suffer_coronary_artery",
            "is_patient_suffer_depression",
            "is_patient_suffer_diabet_L0",
            "is_patient_suffer_diabet_L1",
            "is_patient_suffer_diabet_L2",
            "is_patient_suffer_renal_insufficiency",
            "is_patient_suffer_pulmonary_embolism",
            "is_patient_suffer_HIV_infection",
            "is_patient_suffer_high_cholesterol",
            "is_patient_suffer_hyper_tension",
            "is_patient_suffer_obesity",
            "is_patient_suffer_apnea",
            "is_patient_suffer_osteoporosis",
        ]

        feature_cols = []
        if EXPECTED_COLS:
            feature_cols = list(dict.fromkeys(REQUIRED_FEATURES + EXPECTED_COLS))
        else:
            feature_cols = REQUIRED_FEATURES[:]

        fieldnames = patient_cols + base_cols + feature_cols

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for a in analyses:
            payload = to_dict(a.get("payload_json"))  

            features_row = {k: "" for k in feature_cols}
            for k in feature_cols:
                if k.startswith("is_patient_suffer_"):
                    features_row[k] = "No"
            for k in ["is_arrival_ambulance","is_patient_seen_before_72h","patient_alchol_level"]:
                if k in features_row:
                    features_row[k] = "No"

            for k, v in payload.items():
                if k in features_row:
                    features_row[k] = v

            row = {}
            for c in patient_cols:
                row[c] = patient.get(c, "")
            row["created_at"] = str(a.get("created_at") or "")
            row["Status"] = a.get("label", "")

            for k in feature_cols:
                v = features_row.get(k, "")
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, ensure_ascii=False)
                row[k] = v

            writer.writerow(row)

        csv_data = output.getvalue()
        output.close()

        filename = f"patient_{pat_id}_triage_export_flat.csv"
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print(f"Running on http://{HOST}:{PORT}")
    app.run(debug=True, host=HOST, port=PORT)
