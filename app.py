"""
app.py  —  CompanyLens Flask Backend (Gemini Edition)
Routes:
  POST  /enrich         → scrape + AI enrich one URL
  GET   /results        → return all saved results
  POST  /results/clear  → wipe all results
  GET   /health         → health check
"""

import os
import json
import time
import re
import requests

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from difflib import SequenceMatcher

# Import the modern official Google GenAI Library
from google import genai
from google.genai import types

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

RESULTS_FILE = "results.json"
TARGET_KEYWORDS = ["about", "contact", "services", "team", "company",
                   "solution", "product", "who-we-are", "careers"]

SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SYSTEM_PROMPT = """You are a precise business data extraction assistant.
You extract factual company information from scraped website text.
STRICT RULES:
1. Only use information CLEARLY stated in the provided text.
2. NEVER invent, guess, or hallucinate contact details, addresses, or services.
3. If a field cannot be found, return "" for strings or [] for arrays.
4. Return ONLY a valid JSON object — no markdown fences, no explanation."""

# Initialize the Gemini Client. It will look for the 'GEMINI_API_KEY' env variable.
# If it sees an Anthropic key (sk-ant-), we handle it gracefully inside our enrich function.
try:
    client = genai.Client()
except Exception as e:
    print(f"Warning initializing Gemini Client: {e}")
    client = None

# ─────────────────────────────────────── Persistence ─────────────────────────

def load_results():
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_results(data):
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────── Scraping ────────────────────────────

def fetch_page(url, timeout=12):
    try:
        session = requests.Session()
        resp = session.get(url, headers=SCRAPE_HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"[fetch failed] {url}: {e}")
        return None


def fuzzy_match(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def is_relevant_url(href):
    if not href:
        return False
    path = href.lower().strip("/")
    last = path.split("/")[-1] if "/" in path else path
    for kw in TARGET_KEYWORDS:
        if kw in path:
            return True
        if fuzzy_match(kw, last) > 0.72:
            return True
    return False


def urls_from_sitemap(base_url):
    for sm in ["/sitemap.xml", "/sitemap_index.xml"]:
        html = fetch_page(urljoin(base_url, sm))
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        locs = [t.get_text(strip=True) for t in soup.find_all("loc")]
        relevant = [l for l in locs if is_relevant_url(l)]
        if relevant:
            return relevant[:4]
    return []


def urls_from_homepage(base_url):
    html = fetch_page(base_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(base_url).netloc
    links = set()
    for a in soup.find_all("a", href=True):
        full = urljoin(base_url, a["href"])
        if urlparse(full).netloc == base_domain and is_relevant_url(full):
            links.add(full)
    return list(links)[:4]


def get_pages(base_url):
    pages = urls_from_sitemap(base_url) or urls_from_homepage(base_url)
    if base_url not in pages:
        pages.insert(0, base_url)
    return pages[:5]


REMOVE_TAGS = ["nav", "header", "footer", "script", "style",
               "noscript", "iframe", "form", "svg", "img", "video", "audio"]
NOISE_CLASSES = ["cookie", "popup", "banner", "ad-", "promo", "newsletter", "modal"]


def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(REMOVE_TAGS):
        tag.decompose()
    for tag in soup.find_all(True):
        if not hasattr(tag, "attrs") or tag.attrs is None:
            continue
        cls = " ".join(tag.get("class", []))
        if any(n in cls.lower() for n in NOISE_CLASSES):
            tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def scrape_company(base_url):
    pages = get_pages(base_url)
    parts = []
    all_emails = set()
    all_phones = set()

    for url in pages:
        print(f"  Fetching: {url}")
        html = fetch_page(url)
        if not html:
            continue
        emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", html)
        phones = re.findall(r"[\+]?[\d][\d\s\-\.\(\)]{7,}[\d]", html)
        all_emails.update(emails)
        all_phones.update(phones[:5])
        text = clean_html(html)
        parts.append(f"[PAGE: {url}]\n{text[:2000]}")
        time.sleep(1.0)

    return "\n\n".join(parts), list(all_emails), list(all_phones)


# ─────────────────────────────────────── Gemini AI ───────────────────────────

def empty_record(url, website_name_override=""):
    return {
        "website_name": website_name_override or urlparse(url).netloc,
        "company_name": "",
        "address": "",
        "mobile_number": "",
        "mail": [],
        "core_service": "",
        "target_customer": "",
        "probable_pain_point": "",
        "outreach_opener": "",
        "_url": url
    }


def enrich_with_ai(url, text, emails, phones, website_name_override=""):
    if not text.strip():
        return empty_record(url, website_name_override)

    # Simple validation step to check if the user mistakenly put a Claude key
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key.startswith("sk-ant-"):
        return {**empty_record(url, website_name_override),
                "core_service": "Configuration Error: The GEMINI_API_KEY starts with 'sk-ant-', which is an Anthropic Claude key. Please swap it out for a Google AI Studio key on your Render Dashboard."}

    if not api_key:
        return {**empty_record(url, website_name_override),
                "core_service": "API key not configured — please set GEMINI_API_KEY"}

    contact_hint = ""
    if emails:
        contact_hint += f"\nEmails found on site: {list(set(emails))[:6]}"
    if phones:
        contact_hint += f"\nPhones found on site: {list(set(phones))[:3]}"

    prompt = f"""Extract business information for: {url}
{contact_hint}

Return ONLY a JSON object with these exact keys:
- website_name: brand/website name
- company_name: full company name
- address: physical address if present, else ""
- mobile_number: primary phone number if present, else ""
- mail: array of email addresses if present, else []
- core_service: 1-2 sentence summary of their main product/service
- target_customer: who they serve (industry, size, geography)
- probable_pain_point: key business problem their customers face
- outreach_opener: personalized 1-2 sentence cold outreach referencing their actual work

Scraped website text:
{text[:5500]}"""

    try:
        # Utilize the modern SDK client for gemini-2.5-flash
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.1,
                max_output_tokens=1000,
                # Forces Gemini to natively output pure JSON strings without markdown triple backticks
                response_mime_type="application/json"
            ),
        )
        
        # Load the structured text string directly into a python dict
        result = json.loads(response.text.strip())
        
        if isinstance(result.get("mail"), str):
            result["mail"] = [result["mail"]] if result["mail"] else []
        if website_name_override:
            result["website_name"] = website_name_override
        result["_url"] = url
        return result
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error for {url}: {e}")
        return empty_record(url, website_name_override)
    except Exception as e:
        print(f"AI error for {url}: {e}")
        return {**empty_record(url, website_name_override), "core_service": f"Error: {str(e)}"}


# ─────────────────────────────────────── Flask Routes ────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/enrich", methods=["POST"])
def enrich():
    data = request.get_json(force=True, silent=True) or {}
    url = data.get("url", "").strip()
    website_name = data.get("website_name", "").strip()

    if not url:
        return jsonify({"error": "Missing 'url' field"}), 400
    if not url.startswith("http"):
        url = "https://" + url

    text, emails, phones = scrape_company(url)
    record = enrich_with_ai(url, text, emails, phones, website_name)

    all_results = load_results()
    idx = next((i for i, r in enumerate(all_results) if r.get("_url") == url), None)
    if idx is not None:
        all_results[idx] = record
    else:
        all_results.append(record)
    save_results(all_results)

    return jsonify(record)


@app.route("/results", methods=["GET"])
def get_results():
    return jsonify(load_results())


@app.route("/results/clear", methods=["POST"])
def clear_results():
    save_results([])
    return jsonify({"status": "cleared", "count": 0})


@app.route("/health", methods=["GET"])
def health():
    has_key = bool(os.environ.get("GEMINI_API_KEY", ""))
    return jsonify({"status": "ok", "key_set": has_key})


if __name__ == "__main__":
    print("Starting CompanyLens server on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
