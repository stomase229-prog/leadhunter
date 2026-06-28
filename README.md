# LeadHunter 🏗️
Lead generation app for Bay Area construction & home services

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
python app.py

# 3. Open browser
http://localhost:5000
```

## How to use

1. **Paste your API keys** in the sidebar and click Save Keys
2. **Choose category** (windows, kitchens, bathrooms, etc.)
3. **Select sources** (Yelp and/or Apollo)
4. **Click Fetch Leads** → leads appear in the table
5. **Export to CSV** or **Push to Close CRM**

## Adding API Keys later

- Yelp: yelp.com/developers → Create App
- Apollo: apollo.io → Settings → API → Create Key
- Close CRM: close.com → Settings → Developer → API Keys

## File Structure

```
leads_app/
├── app.py           ← main server
├── requirements.txt
├── leads.json       ← auto-created, stores your leads
└── templates/
    └── index.html   ← web UI
```
