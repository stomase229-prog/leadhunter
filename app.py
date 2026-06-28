from flask import Flask, render_template, jsonify, request, send_file
import requests
import csv
import os
import json
from datetime import datetime

template_folder = 'Templates'

# ─── CONFIG ───────────────────────────────────────────────────────────────────
CONFIG = {
    "yelp_api_key":      "",   # yelp.com/developers
    "apollo_api_key":    "",   # apollo.io → Settings → API
    "close_api_key":     "",   # close.com → Settings → Developer → API Keys
    "facebook_token":    "",   # developers.facebook.com → App Token
    "linkedin_token":    "",   # linkedin.com/developers → Access Token
    "angi_api_key":      "",   # pro.angi.com → API access (manual approval)
    "thumbtack_key":     "",   # partnerships@thumbtack.com (manual approval)
    "houzz_api_key":     "",   # developers.houzz.com (manual approval)
}

LEADS_FILE = "leads.json"

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def load_leads():
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE) as f:
            return json.load(f)
    return []

def save_leads(leads):
    with open(LEADS_FILE, "w") as f:
        json.dump(leads, f, indent=2)

def make_lead(source, name, phone="", email="", address="", rating="", url="", extra=None):
    return {
        "source":     source,
        "name":       name,
        "phone":      phone,
        "email":      email,
        "address":    address,
        "rating":     rating,
        "url":        url,
        "extra":      extra or {},
        "fetched_at": datetime.now().isoformat()
    }

# ─── YELP ────────────────────────────────────────────────────────────────────
def fetch_yelp(category, location, limit=20):
    if not CONFIG["yelp_api_key"]:
        return [], "Yelp API key missing"
    try:
        r = requests.get(
            "https://api.yelp.com/v3/businesses/search",
            headers={"Authorization": f"Bearer {CONFIG['yelp_api_key']}"},
            params={"term": category, "location": location, "limit": limit},
            timeout=10
        )
        r.raise_for_status()
        leads = []
        for b in r.json().get("businesses", []):
            leads.append(make_lead(
                "Yelp", b.get("name",""),
                phone=b.get("phone",""),
                address=", ".join(b.get("location",{}).get("display_address",[])),
                rating=b.get("rating",""),
                url=b.get("url",""),
                extra={"review_count": b.get("review_count",0)}
            ))
        return leads, None
    except Exception as e:
        return [], str(e)

# ─── APOLLO ──────────────────────────────────────────────────────────────────
def fetch_apollo(category, location, limit=20):
    if not CONFIG["apollo_api_key"]:
        return [], "Apollo API key missing"
    try:
        r = requests.post(
            "https://api.apollo.io/v1/mixed_people/search",
            headers={"Content-Type":"application/json","X-Api-Key": CONFIG["apollo_api_key"]},
            json={"q_keywords": category, "person_locations": [location], "per_page": limit},
            timeout=10
        )
        r.raise_for_status()
        leads = []
        for p in r.json().get("people", []):
            leads.append(make_lead(
                "Apollo",
                f"{p.get('first_name','')} {p.get('last_name','')}".strip(),
                phone=(p.get("phone_numbers") or [{}])[0].get("raw_number",""),
                email=p.get("email",""),
                address=f"{p.get('city','')}, {p.get('state','')}",
                url=p.get("linkedin_url",""),
                extra={"title": p.get("title",""), "company": p.get("organization",{}).get("name","")}
            ))
        return leads, None
    except Exception as e:
        return [], str(e)

# ─── FACEBOOK LEAD ADS ────────────────────────────────────────────────────────
def fetch_facebook(category, location, limit=20):
    if not CONFIG["facebook_token"]:
        return [], "Facebook token missing"
    try:
        # Search for local businesses via Facebook Graph API
        r = requests.get(
            "https://graph.facebook.com/v18.0/search",
            params={
                "type": "place",
                "q": f"{category} {location}",
                "fields": "name,phone,emails,location,website,overall_star_rating",
                "limit": limit,
                "access_token": CONFIG["facebook_token"]
            },
            timeout=10
        )
        r.raise_for_status()
        leads = []
        for b in r.json().get("data", []):
            loc = b.get("location", {})
            leads.append(make_lead(
                "Facebook",
                b.get("name",""),
                phone=b.get("phone",""),
                email=(b.get("emails") or [""])[0],
                address=f"{loc.get('street','')}, {loc.get('city','')}, {loc.get('state','')}",
                rating=b.get("overall_star_rating",""),
                url=b.get("website",""),
            ))
        return leads, None
    except Exception as e:
        return [], str(e)

# ─── LINKEDIN ─────────────────────────────────────────────────────────────────
def fetch_linkedin(category, location, limit=20):
    if not CONFIG["linkedin_token"]:
        return [], "LinkedIn token missing"
    try:
        # LinkedIn People Search API
        r = requests.get(
            "https://api.linkedin.com/v2/people",
            headers={
                "Authorization": f"Bearer {CONFIG['linkedin_token']}",
                "X-Restli-Protocol-Version": "2.0.0"
            },
            params={
                "q": "search",
                "keywords": f"{category} {location}",
                "count": limit
            },
            timeout=10
        )
        r.raise_for_status()
        leads = []
        for p in r.json().get("elements", []):
            name = f"{p.get('localizedFirstName','')} {p.get('localizedLastName','')}".strip()
            leads.append(make_lead(
                "LinkedIn", name,
                url=f"https://www.linkedin.com/in/{p.get('id','')}",
                extra={"headline": p.get("localizedHeadline","")}
            ))
        return leads, None
    except Exception as e:
        return [], str(e)

# ─── ANGI ─────────────────────────────────────────────────────────────────────
def fetch_angi(category, location, limit=20):
    if not CONFIG["angi_api_key"]:
        return [], "Angi API key missing"
    try:
        r = requests.get(
            "https://www.angi.com/api/v1/pros/search",
            headers={"Authorization": f"Bearer {CONFIG['angi_api_key']}",
                     "Content-Type": "application/json"},
            params={"category": category, "location": location, "limit": limit},
            timeout=10
        )
        r.raise_for_status()
        leads = []
        for pro in r.json().get("pros", []):
            leads.append(make_lead(
                "Angi",
                pro.get("businessName",""),
                phone=pro.get("phone",""),
                email=pro.get("email",""),
                address=pro.get("address",""),
                rating=pro.get("rating",""),
                url=pro.get("profileUrl",""),
                extra={"years_in_business": pro.get("yearsInBusiness",""),
                       "num_reviews": pro.get("numReviews",0)}
            ))
        return leads, None
    except Exception as e:
        return [], str(e)

# ─── THUMBTACK ────────────────────────────────────────────────────────────────
def fetch_thumbtack(category, location, limit=20):
    if not CONFIG["thumbtack_key"]:
        return [], "Thumbtack API key missing"
    try:
        r = requests.get(
            "https://api.thumbtack.com/v2/pros",
            headers={"Authorization": f"Bearer {CONFIG['thumbtack_key']}",
                     "Content-Type": "application/json"},
            params={"service": category, "location": location, "limit": limit},
            timeout=10
        )
        r.raise_for_status()
        leads = []
        for pro in r.json().get("pros", []):
            leads.append(make_lead(
                "Thumbtack",
                pro.get("name",""),
                phone=pro.get("phone",""),
                email=pro.get("email",""),
                address=pro.get("location",""),
                rating=pro.get("rating",""),
                url=pro.get("url",""),
                extra={"hired_count": pro.get("hiredCount",0)}
            ))
        return leads, None
    except Exception as e:
        return [], str(e)

# ─── HOUZZ ────────────────────────────────────────────────────────────────────
def fetch_houzz(category, location, limit=20):
    if not CONFIG["houzz_api_key"]:
        return [], "Houzz API key missing"
    try:
        r = requests.get(
            "https://www.houzz.com/api/v1/pros",
            headers={"Authorization": f"Bearer {CONFIG['houzz_api_key']}",
                     "Content-Type": "application/json"},
            params={"category": category, "location": location, "results": limit},
            timeout=10
        )
        r.raise_for_status()
        leads = []
        for pro in r.json().get("professionals", []):
            leads.append(make_lead(
                "Houzz",
                pro.get("displayName",""),
                phone=pro.get("phone",""),
                email=pro.get("email",""),
                address=pro.get("location",""),
                rating=pro.get("avgRating",""),
                url=pro.get("profileUrl",""),
                extra={"projects": pro.get("projectCount",0),
                       "reviews":  pro.get("reviewCount",0)}
            ))
        return leads, None
    except Exception as e:
        return [], str(e)

# ─── PUSH TO CLOSE CRM ───────────────────────────────────────────────────────
def push_to_close(lead):
    if not CONFIG["close_api_key"]:
        return False, "Close CRM API key missing"
    try:
        payload = {
            "name": lead["name"],
            "contacts": [{
                "name": lead["name"],
                "phones": [{"phone": lead["phone"], "type": "office"}] if lead["phone"] else [],
                "emails": [{"email": lead["email"], "type": "office"}] if lead["email"] else [],
            }],
            "addresses": [{"address_1": lead["address"]}] if lead["address"] else [],
            "custom": {
                "Source":  lead["source"],
                "Rating":  str(lead["rating"]),
                "URL":     lead["url"],
            }
        }
        r = requests.post(
            "https://api.close.com/api/v1/lead/",
            auth=(CONFIG["close_api_key"], ""),
            json=payload, timeout=10
        )
        r.raise_for_status()
        return True, None
    except Exception as e:
        return False, str(e)

# ─── SOURCE MAP ───────────────────────────────────────────────────────────────
SOURCE_MAP = {
    "yelp":      fetch_yelp,
    "apollo":    fetch_apollo,
    "facebook":  fetch_facebook,
    "linkedin":  fetch_linkedin,
    "angi":      fetch_angi,
    "thumbtack": fetch_thumbtack,
    "houzz":     fetch_houzz,
}

# ─── ROUTES ──────────────────────────────────────────────────────────────────
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
    data     = request.json
    sources  = data.get("sources", [])
    category = data.get("category", "contractor")
    location = data.get("location", "San Francisco, CA")
    limit    = int(data.get("limit", 20))

    all_leads = load_leads()
    results   = {"added": 0, "errors": [], "by_source": {}}

    for src in sources:
        fn = SOURCE_MAP.get(src)
        if not fn:
            continue
        leads, err = fn(category, location, limit)
        if err:
            results["errors"].append(f"{src.capitalize()}: {err}")
        else:
            all_leads.extend(leads)
            results["added"] += len(leads)
            results["by_source"][src] = len(leads)

    save_leads(all_leads)
    results["total"] = len(all_leads)
    return jsonify(results)

@app.route("/api/leads")
def api_leads():
    leads  = load_leads()
    source = request.args.get("source", "")
    if source:
        leads = [l for l in leads if l["source"].lower() == source.lower()]
    return jsonify(leads)

@app.route("/api/stats")
def api_stats():
    leads = load_leads()
    stats = {}
    for l in leads:
        stats[l["source"]] = stats.get(l["source"], 0) + 1
    return jsonify({"total": len(leads), "by_source": stats})

@app.route("/api/push_crm", methods=["POST"])
def api_push_crm():
    leads   = load_leads()
    indices = request.json.get("indices", list(range(len(leads))))
    pushed, errors = 0, []
    for i in indices:
        if i < len(leads):
            ok, err = push_to_close(leads[i])
            if ok: pushed += 1
            elif err: errors.append(err)
    return jsonify({"pushed": pushed, "errors": errors})

@app.route("/api/export/csv")
def export_csv():
    leads = load_leads()
    if not leads:
        return jsonify({"error": "No leads"}), 400
    path = "/tmp/leads_export.csv"
    # Flatten extra dict into columns
    flat = []
    for l in leads:
        row = {k: v for k, v in l.items() if k != "extra"}
        row.update(l.get("extra", {}))
        flat.append(row)
    all_keys = list(dict.fromkeys(k for r in flat for k in r.keys()))
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(flat)
    return send_file(path, as_attachment=True, download_name="leads.csv")

@app.route("/api/clear", methods=["POST"])
def clear_leads():
    save_leads([])
    return jsonify({"status": "cleared"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
