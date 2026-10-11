import io
import io
import os
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from pypdf import PdfReader

load_dotenv()

app = Flask(__name__)
CORS(app)

IBM_API_KEY = os.getenv("IBM_API_KEY")
IAM_URL = "https://iam.cloud.ibm.com/identity/token"
SCORING_URL = "https://au-syd.ml.cloud.ibm.com/ml/v4/deployments/01a12c00-c071-77dc-9faf-b2a342e56691/predictions?version=2021-05-01"

def extract_pdf_text(file_storage):
    """Extract text from an uploaded PDF stream."""
    reader = PdfReader(io.BytesIO(file_storage.read()))
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text.strip()

@app.route("/analyze", methods=["POST"])
def analyze():
    target_jd = request.form.get("target_jd", "").strip()
    resume_text = request.form.get("resume_text", "").strip()

    # Extract text from uploaded PDF if provided
    if "resume_file" in request.files:
        uploaded_file = request.files["resume_file"]
        if uploaded_file and uploaded_file.filename.lower().endswith(".pdf"):
            pdf_extracted = extract_pdf_text(uploaded_file)
            if pdf_extracted:
                resume_text = pdf_extracted

    if not resume_text:
        return jsonify({"error": "No resume text or valid PDF file provided."}), 400
    if not target_jd:
        return jsonify({"error": "Job description is required."}), 400

    # 1. Exchange API key for IAM Bearer token
    token_resp = requests.post(
        IAM_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": IBM_API_KEY}
    )
    if token_resp.status_code != 200:
        return jsonify({"error": "Failed to authenticate with IBM Cloud IAM"}), 401

    bearer_token = token_resp.json().get("access_token")

    # 2. Forward payload to watsonx WML scoring endpoint
    payload = {
        "input_data": [{
            "fields": ["resume_text", "target_jd"],
            "values": [{"resume_text": resume_text, "target_jd": target_jd}]
        }]
    }

    scoring_resp = requests.post(
        SCORING_URL,
        headers={"Authorization": f"Bearer {bearer_token}", "Content-Type": "application/json"},
        json=payload
    )

    return jsonify(scoring_resp.json()), scoring_resp.status_code

if __name__ == "__main__":
    print("Proxy running with PDF upload & secure backend key at http://127.0.0.1:5000/analyze")
    app.run(host="127.0.0.1", port=5000, debug=True)