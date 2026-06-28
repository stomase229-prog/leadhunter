from flask import Flask, render_template, jsonify, request, send_file
import requests
import csv
import os
import json
from datetime import datetime

app = Flask(__name__, template_folder='Templates')

CONFIG = {
    "yelp_api_key": "",
    "apollo_api_key": "",
    "close_api_key": "",
    "facebook_token": "",
    "linkedin_token": "",
    "angi_api_key": "",
    "thumbtack_key": "",
    "houzz_api_key": "",
}

LEADS_FILE = "leads.json"

def load_leads():
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE) as f:
            return json.load(f)
    return []

def save_leads(leads):
    with open(LEADS_FILE, "w") as f:
        json.dump(leads, f, indent=2)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "POST":
        for k, v in request.json.items():
            if k in CONFIG:
                CONFIG[k] = v
        return jsonify({"status": "saved"})
    return jsonify({k: ("set" if v else "missing") for k, v in CONFIG.items()})

@app.route("/api/fetch", methods=["POST"])
def api_fetch():
    data = request.json
    sources = data.get("sources", [])
    category = data.get("category", "contractor")
    location = data.get("location", "San Francisco, CA")
    limit = int(data.get("limit", 20))

    all_leads = load_leads()
    results = {"added": 0, "errors": [], "by_source": {}}

    if "yelp" in sources:
        if not CONFIG["yelp_api_key"]:
            results["errors"].append("Yelp: API key missing")
        else:
            try:
                r = requests.get(
                    "https://api.yelp.com/v3/businesses/search",
                    headers={"Authorization": f"Bearer {CONFIG['yelp_api_key']}"},
                    params={"term": category, "location": location, "limit": limit},
                    timeout=10
                )
                r.raise_for_status()
                for b in r.json().get("businesses", []):
                    all_leads.append({
                        "source": "Yelp",
                        "name": b.get("name", ""),
                        "phone": b.get("phone", ""),
                        "email": "",
                        "address": ", ".join(b.get("location", {}).get("display_address", [])),
                        "rating": b.get("rating", ""),
                        "url": b.get("url", ""),
                        "fetched_at": datetime.now().isoformat()
                    })
                results["added"] += limit
                results["by_source"]["yelp"] = limit
            except Exception as e:
                results["errors"].append(f"Yelp: {str(e)}")

    save_leads(all_leads)
    results["total"] = len(all_leads)
    return jsonify(results)

@app.route("/api/leads")
def api_leads():
    leads = load_leads()
    source = request.args.get("source", "")
    if source:
        leads = [l for l in leads if l["source"].lower() == source.lower()]
    return jsonify(leads)

@app.route("/api/export/csv")
def export_csv():
    leads = load_leads()
    if not leads:
        return jsonify({"error": "No leads"}), 400
    path = "/tmp/leads_export.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=leads[0].keys())
        writer.writeheader()
        writer.writerows(leads)
    return send_file(path, as_attachment=True, download_name="leads.csv")

@app.route("/api/clear", methods=["POST"])
def clear_leads():
    save_leads([])
    return jsonify({"status": "cleared"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
