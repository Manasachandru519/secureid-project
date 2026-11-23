import os, uuid, hashlib
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from storage import Store
from security import sha256_text, encrypt_json
from fraud_model import FraudModel
from blockchain import make_block, verify_chain

load_dotenv()
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": os.getenv("CORS_ORIGINS", "*").split(",")}})
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
store = Store()
fraud = FraudModel()
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

def safe_identity(row):
    return {k: row[k] for k in ["id","name","email","identity_hash","status","risk_score","risk_level","created_at"]}

def read_ocr(file):
    if not file or not file.filename:
        return "", 0.95
    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"]:
        return "", 0.65
    path = UPLOAD_DIR / (uuid.uuid4().hex + suffix)
    file.save(path)
    try:
        import pytesseract
        from PIL import Image
        cmd = os.getenv("TESSERACT_CMD", "").strip()
        if cmd: pytesseract.pytesseract.tesseract_cmd = cmd
        text = pytesseract.image_to_string(Image.open(path))[:4000]
        confidence = 0.88 if len(text.strip()) > 15 else 0.48
        return text, confidence
    except Exception:
        return "OCR engine not configured; document stored for manual review.", 0.65
    finally:
        try: path.unlink(missing_ok=True)
        except Exception: pass

@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "SecureID API", "database": "MongoDB" if store.mongo is not None else "SQLite demo fallback"})

@app.post("/api/register")
def register():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    identity_type = request.form.get("identity_type", "Other").strip()
    identity_number = request.form.get("identity_number", "").strip()
    if not name or not email or not identity_number:
        return jsonify({"error": "Name, email and identity number are required."}), 400
    if store.get_identity_by_email(email):
        return jsonify({"error": "Duplicate registration: this email is already registered."}), 409

    duplicate = 1 if any(x.get("identity_hash") == sha256_text(identity_number) for x in store.list_identities()) else 0
    ocr_text, ocr_conf = read_ocr(request.files.get("document"))
    # A simple consistency signal for the demonstration, not a real document-authenticity test.
    mismatch = 1 if (ocr_text and "not configured" not in ocr_text.lower() and len(ocr_text.strip()) < 8) else 0
    result = fraud.predict(ocr_confidence=ocr_conf, duplicate=duplicate, mismatch=mismatch)
    identity_id = "SID-" + uuid.uuid4().hex[:10].upper()
    now = datetime.now(timezone.utc).isoformat()
    private_data = {"name":name,"email":email,"phone":phone,"identity_type":identity_type,
                    "identity_number":identity_number}
    digest = sha256_text(f"{name.lower()}|{email}|{identity_type}|{identity_number}")
    status = "Pending Review" if result["score"] >= 40 else "Verified"
    item = {"id":identity_id,"name":name,"email":email,"encrypted_data":encrypt_json(private_data),
            "identity_hash":digest,"status":status,"risk_score":result["score"],
            "risk_level":result["level"],"created_at":now,"ocr_text":encrypt_json({"text":ocr_text}) if ocr_text else ""}
    store.add_identity(item)
    blocks = store.list_blocks()
    previous = blocks[-1]["block_hash"] if blocks else "0" * 64
    store.add_block(make_block(identity_id, digest, previous, len(blocks)+1))
    if result["score"] >= 40 or duplicate:
        store.add_alert(identity_id,email,result["score"],"; ".join(result["reasons"]))
    return jsonify({"message":"Registration completed","identity":safe_identity(item),
                    "fraud":result,"ocr_note":"OCR text extracted for review" if ocr_text else "No document image supplied"}), 201

@app.get("/api/identities")
def identities():
    return jsonify([safe_identity(x) for x in store.list_identities()])

@app.get("/api/dashboard")
def dashboard():
    users = store.list_identities()
    alerts = store.list_alerts()
    total = len(users)
    verified = sum(1 for x in users if x["status"] == "Verified")
    pending = total - verified
    high = sum(1 for x in users if x["risk_score"] >= 70)
    return jsonify({"total_users":total,"verified":verified,"pending":pending,"high_risk":high,
                    "alerts":len(alerts),"identities":[safe_identity(x) for x in users[:30]],
                    "recent_alerts":alerts[:8],"database":"MongoDB" if store.mongo is not None else "SQLite demo fallback"})

@app.get("/api/alerts")
def alerts():
    return jsonify(store.list_alerts())

@app.post("/api/simulate-activity")
def simulate_activity():
    data = request.get_json(silent=True) or {}
    result = fraud.predict(failed_attempts=int(data.get("failed_attempts",6)),
        ocr_confidence=float(data.get("ocr_confidence",.52)), duplicate=int(data.get("duplicate",0)),
        device_changes=int(data.get("device_changes",3)), mismatch=int(data.get("mismatch",1)))
    fake_id = "ACT-" + uuid.uuid4().hex[:8].upper()
    store.add_alert(fake_id, data.get("email","demo@example.com"), result["score"], "; ".join(result["reasons"]))
    return jsonify({"activity_id":fake_id,"fraud":result}), 201

@app.get("/api/blocks")
def blocks():
    chain = store.list_blocks()
    return jsonify({"blocks":chain,"valid":verify_chain(chain),"count":len(chain)})

@app.post("/api/verify-chain")
def verify():
    chain = store.list_blocks()
    return jsonify({"valid":verify_chain(chain),"count":len(chain),
                    "message":"Blockchain records verified" if verify_chain(chain) else "Hash mismatch detected"})

@app.post("/api/identities/<identity_id>/status")
def update_status(identity_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in ["Verified","Rejected","Pending Review"]:
        return jsonify({"error":"Invalid status"}), 400
    found = next((x for x in store.list_identities() if x["id"] == identity_id), None)
    if not found: return jsonify({"error":"Identity not found"}), 404
    store.update_status(identity_id,status)
    return jsonify({"message":"Status updated","status":status})

@app.get("/api/reports")
def reports():
    users = store.list_identities()
    alerts = store.list_alerts()
    return jsonify({"generated_at":datetime.now(timezone.utc).isoformat(),
        "summary":{"registrations":len(users),"alerts":len(alerts),
        "verified":sum(x["status"]=="Verified" for x in users),
        "pending":sum(x["status"]!="Verified" for x in users)},
        "risk_distribution":{"low":sum(x["risk_score"]<40 for x in users),
        "medium":sum(40<=x["risk_score"]<70 for x in users),"high":sum(x["risk_score"]>=70 for x in users)}})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",5000)), debug=os.getenv("FLASK_DEBUG","0")=="1")
