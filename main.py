#!/usr/bin/env python3
import os
import json
import requests
from datetime import datetime

#  CONFIG — only edit LOCATION_IDS if you ever want to expand
LOCATION_IDS = [9117, 9118, 9119]  # JLT Clusters D, E, F
PURPOSES = ["for-rent", "for-sale"]
DATA_FILE = "last_seen.json"

# Environment variables (from GitHub secrets)
RAPIDAPI_KEY = os.getenv("BAYUT_RAPIDAPI_KEY")
RAPIDAPI_HOST = "bayut-api1.p.rapidapi.com"
ULTRAMSG_INSTANCE = os.getenv("ULTRAMSG_INSTANCE_ID")
ULTRAMSG_TOKEN = os.getenv("ULTRAMSG_TOKEN")
WHATSAPP_TO = os.getenv("WHATSAPP_TO")

if not (RAPIDAPI_KEY and ULTRAMSG_INSTANCE and ULTRAMSG_TOKEN and WHATSAPP_TO):
    raise SystemExit("Missing one or more required environment variables.")

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST,
    "Content-Type": "application/json"
}

def load_seen():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f).get("seen_ids", []))
    return set()

def save_seen(seen_ids):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"seen_ids": list(seen_ids)}, f)

def fetch_listings(purpose):
    url = f"https://{RAPIDAPI_HOST}/properties_search"
    body = {
        "purpose": purpose,
        "locations_ids": LOCATION_IDS,
        "page": 0,
        "langs": "en",
        "index": "latest"
    }
    resp = requests.post(url, headers=HEADERS, json=body, timeout=20)
    resp.raise_for_status()
    return resp.json().get("results", [])

def format_message(item, purpose):
    title = item.get("title") or item.get("headline") or "Listing"
    price = item.get("price") or item.get("price_display") or "N/A"
    area = item.get("area") or ""
    community = (item.get("full", {}) or {}).get("cluster", {}).get("name", "")
    agent = (item.get("agency") or {}).get("name", "")
    link = item.get("url") or item.get("permalink") or ""
    if link and not link.startswith("http"):
        link = "https://www.bayut.com" + link
    lines = [f"{'RENT' if purpose=='for-rent' else 'SALE'}: {title}",
             f"Price: {price}", f"Area: {area}", f"Area: {community}", f"Agent: {agent}", f"Link: {link}", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")]
    return "\n".join([line for line in lines if line])

def send_whatsapp(msg):
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE}/messages/chat"
    payload = {"token": ULTRAMSG_TOKEN, "to": WHATSAPP_TO, "body": msg}
    resp = requests.post(url, data=payload, timeout=10)
    resp.raise_for_status()

def main():
    seen = load_seen()
    new_seen = set(seen)
    for purpose in PURPOSES:
        listings = fetch_listings(purpose)
        for item in listings:
            lid = str(item.get("id") or "")
            if lid and lid not in seen:
                msg = format_message(item, purpose)
                try:
                    send_whatsapp(msg)
                    new_seen.add(lid)
                    print("Sent alert for", lid)
                except Exception as e:
                    print("Failed to send for", lid, ":", e)
    save_seen(new_seen)
    print("Watch complete at", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

if __name__ == "__main__":
    main()
