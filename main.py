# KGFBS – Kamgo Facebook Sourcing
# Proof of Concept – real scraping requires an Apify API key (FB anti-bot protection).

import requests
import argparse
from mapper import map_fb_event_to_kamgo, prepare_for_api
from categorizer import categorize_event
from dedup import init_db, is_duplicate, update_event, save_event, close_db

SUBJECTS_API = "https://podujatia.relaxos.sk/api/subjects"
SUBJECTS_TOKEN = "KsHo4tRw8kfGAAN"

MOCK_FB_EVENTS = [
    {
        "fbId": "123456789",
        "fbUrl": "https://www.facebook.com/events/123456789",
        "name": "Jazzový večer v Košiciach",
        "description": "Príďte si vychutnať živú jazzovú hudbu v centre mesta.",
        "placeName": "Kulturpark Košice",
        "city": "Košice",
        "street": "Kukučínova 2",
        "startAt": "2026-04-15T19:00:00",
        "finishAt": "2026-04-15T22:00:00",
        "imageUrl": "https://example.com/image.jpg",
        "tags": ["Hudba", "Jazz"],
        "ticketUrl": "https://predpredaj.sk/example"
    },
    {
        "fbId": "987654321",
        "fbUrl": "https://www.facebook.com/events/987654321",
        "name": "Detský karneval",
        "description": "Karneval pre deti od 3 do 10 rokov. Súťaže, masky, zábava!",
        "placeName": "Dom kultúry Prešov",
        "city": "Prešov",
        "street": "Námestie mieru 1",
        "startAt": "2026-04-20T10:00:00",
        "finishAt": "2026-04-20T14:00:00",
        "imageUrl": "https://example.com/image2.jpg",
        "tags": ["Pre deti"],
        "ticketUrl": None
    },
    {
        "fbId": "111222333",
        "fbUrl": "https://www.facebook.com/events/111222333",
        "name": "Výstava moderného umenia",
        "description": "Výstava súčasných slovenských umelcov.",
        "placeName": "Galéria bez FB stránky",
        "city": "48.143489, 17.107137",  # GPS coordinates – mapper will handle this
        "street": "48.143489, 17.107137",
        "startAt": "2026-05-01T10:00:00",
        "finishAt": None,
        "imageUrl": None,
        "tags": ["Kultúra a umenie"],
        "ticketUrl": None
    }
]

MOCK_SUBJECTS = [
    {"name": "Kulturpark Košice", "kamgoId": 101, "fbId": "kulturpark.ke",
     "fbUrl": "https://www.facebook.com/kulturpark.ke", "webUrl": "", "venue": "venue"},
    {"name": "Štátne divadlo Košice", "kamgoId": 102, "fbId": "sdke.sk",
     "fbUrl": "https://www.facebook.com/sdke.sk", "webUrl": "", "venue": "venue"},
]


def fetch_subjects(offline=False):
    if offline:
        return MOCK_SUBJECTS
    resp = requests.get(SUBJECTS_API, headers={"token": SUBJECTS_TOKEN})
    resp.raise_for_status()
    return resp.json()


def scrape_events_apify(fb_page_id: str, apify_token: str, initial: bool = False) -> list:
    url = "https://api.apify.com/v2/acts/apify~facebook-events-scraper/run-sync-get-dataset-items"
    payload = {
        "startUrls": [{"url": f"https://www.facebook.com/{fb_page_id}/events"}],
        "maxItems": 200 if initial else 10
    }
    resp = requests.post(url, json=payload, params={"token": apify_token})
    resp.raise_for_status()
    return resp.json()


def send_to_kamgo_api(event: dict, kamgo_api_token: str, method: str = "POST"):
    api_payload = prepare_for_api(event)

    # PoC: print instead of real HTTP call
    action = "POST (new)" if method == "POST" else "PUT (update)"
    print(f"  ✓ [{action}] {event['name']} | {event['startAt']} | {event.get('city', '?')} | "
          f"FB: {event.get('category') or '-'} | AI: {event.get('aiCategory', 'N/A')}")

    # Production:
    # kamgo_url = "https://api.kamgo.sk/v1/events"
    # headers = {"Authorization": f"Bearer {kamgo_api_token}"}
    # if method == "POST":
    #     resp = requests.post(kamgo_url, json=api_payload, headers=headers)
    # else:
    #     resp = requests.put(f"{kamgo_url}/{event['fbId']}", json=api_payload, headers=headers)
    # resp.raise_for_status()


def process_subject(subject: dict, events: list, kamgo_api_token: str):
    results = {"sent": 0, "updated": 0, "errors": 0}

    for raw_event in events:
        try:
            event = map_fb_event_to_kamgo(raw_event, subject)
            event["aiCategory"] = categorize_event(event)

            if is_duplicate(event):
                changed = update_event(event)
                if changed:
                    # API first – if it fails, DB stays at old state and cron will retry
                    send_to_kamgo_api(event, kamgo_api_token, method="PUT")
                    save_event(event)
                    results["updated"] += 1
                continue

            # New event: send to API first, save to DB only on success
            send_to_kamgo_api(event, kamgo_api_token, method="POST")
            save_event(event)
            results["sent"] += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            results["errors"] += 1

    return results


def main(mode: str):
    print("=== KGFBS Proof of Concept ===\n")
    init_db(mock=(mode == "mock"))

    offline = (mode == "mock")
    print("Loading subjects" + (" (offline mock)" if offline else " from Kamgo API") + "...")
    subjects = fetch_subjects(offline=offline)
    print(f"Total subjects: {len(subjects)}\n")

    if mode == "mock":
        print("Mode: MOCK (simulated FB events, in-memory DB)\n")
        for i, subject in enumerate(subjects[:2]):
            print(f"[{i+1}] Processing: {subject['name']} (fbId: {subject['fbId']})")
            results = process_subject(subject, MOCK_FB_EVENTS, kamgo_api_token="mock")
            print(f"    New: {results['sent']} | Updated: {results['updated']} | Errors: {results['errors']}\n")

    elif mode == "initial":
        import os
        apify_token = os.getenv("APIFY_TOKEN")
        if not apify_token:
            print("ERROR: Set APIFY_TOKEN environment variable")
            return
        print("Mode: INITIAL (scraping all future events, SQLite DB)\n")
        for subject in subjects:
            print(f"Processing: {subject['name']}")
            events = scrape_events_apify(subject["fbId"], apify_token, initial=True)
            results = process_subject(subject, events, kamgo_api_token="...")
            print(f"  → {results}\n")

    elif mode == "live":
        import os
        apify_token = os.getenv("APIFY_TOKEN")
        if not apify_token:
            print("ERROR: Set APIFY_TOKEN environment variable")
            return
        print("Mode: LIVE (incremental feed, SQLite DB)\n")
        for subject in subjects:
            print(f"Processing: {subject['name']}")
            events = scrape_events_apify(subject["fbId"], apify_token, initial=False)
            results = process_subject(subject, events, kamgo_api_token="...")
            print(f"  → {results}\n")

    close_db()
    print("\n=== Done ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["mock", "initial", "live"],
        default="mock",
        help="mock: simulated data | initial: first-time full scrape | live: incremental feed"
    )
    args = parser.parse_args()
    main(args.mode)
