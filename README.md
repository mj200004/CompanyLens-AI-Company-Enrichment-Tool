# CompanyLens — AI Company Enrichment Tool

A Flask web app that scrapes company websites and uses Claude AI to extract structured business intelligence: services, target customers, contact info, and personalized outreach openers.

## Live Demo
Deployed on Render/Railway — see the live URL in the deployment settings.

## Features
- Paste any company URL → get structured JSON profile
- Extracts: company name, address, email, phone, core service, target customer, pain points, outreach message
- Stores all results in a table — view, filter, export
- Clean responsive UI — works on mobile and desktop

## Tech Stack
- **Backend**: Python + Flask + BeautifulSoup + Anthropic Claude API
- **Frontend**: Vanilla HTML/CSS/JS (served as static files by Flask)
- **Deploy**: Render or Railway (free tier)

## Local Setup

```bash
git clone <your-repo-url>
cd company-enricher
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
python app.py
# Open http://localhost:5000
```

## Deploy on Railway (Recommended — Free)

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
3. Select this repo → Railway auto-detects Python
4. Go to **Variables** tab → Add: `ANTHROPIC_API_KEY` = your key
5. Click **Deploy** — get a public URL in ~2 minutes

## Deploy on Render (Also Free)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1`
6. Under **Environment** → Add: `ANTHROPIC_API_KEY` = your key
7. Click **Create Web Service**

## File Structure

```
├── app.py              # Flask backend — all scraping + AI logic
├── static/
│   └── index.html      # Frontend UI (single file)
├── requirements.txt
├── Procfile            # For Render
├── railway.json        # For Railway
└── render.yaml         # For Render (optional)
```

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Serves the frontend UI |
| POST | `/enrich` | Enrich a company URL |
| GET | `/results` | Get all saved results |
| POST | `/results/clear` | Clear all results |
| GET | `/health` | Health check |

## Usage (API)

```bash
curl -X POST https://your-app.onrender.com/enrich \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.infosys.com"}'
```
