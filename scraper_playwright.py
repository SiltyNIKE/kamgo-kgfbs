# Alternatívny scraper – Playwright namiesto Apify.
#
# KEDY POUŽIŤ:
#   - Apify je príliš drahý alebo nechceme závisieť od externej služby
#   - Máme vlastný server kde môžeme spustiť headless prehliadač
#
# NEVÝHODY oproti Apify:
#   - Facebook aktívne detekuje a blokuje headless prehliadače
#   - Vyžaduje rotating proxies aby sa predišlo banu IP (aj tak ~$20-40/mes)
#   - Veľmi nestabilné – FB môže zmeniť DOM štruktúru a scraper prestane fungovať
#   - Ťažšie škálovanie – 4000 stránok = veľa paralelných sessions
#   - Vyžaduje údržbu pri každej zmene FB UI
#
# INŠTALÁCIA:
#   pip install playwright
#   playwright install chromium
#
# DISCLAIMER: Tento súbor je proof of concept.
# Reálne nasadenie vyžaduje riešenie FB anti-bot ochrany (proxies, fingerprinting).

# from playwright.sync_api import sync_playwright
# import time
# import re

# Ukážka ako by vyzeral scraper jednej FB stránky cez Playwright
# (zakomentované – vyžaduje playwright install)

"""
def scrape_fb_page_playwright(fb_page_id: str, proxy: str = None) -> list:
    # Scrapuje eventy z jednej FB stránky cez headless Chromium.
    # proxy: voliteľný rotating proxy v tvare "http://user:pass@host:port"

    events = []

    with sync_playwright() as p:
        # Spustenie headless prehliadača s voliteľným proxy
        browser = p.chromium.launch(
            headless=True,
            proxy={"server": proxy} if proxy else None
        )

        # User-agent nastavíme na bežný prehliadač aby sme nevyzerali ako bot
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        # Otvoríme stránku s eventmi
        url = f"https://www.facebook.com/{fb_page_id}/events"
        page.goto(url, wait_until="networkidle", timeout=30000)

        # Čakáme na načítanie eventov (FB renderuje cez JavaScript)
        time.sleep(3)

        # Extrakcia eventov z DOM – krehká časť, závisí od FB štruktúry
        event_links = page.query_selector_all('a[href*="/events/"]')

        for link in event_links:
            href = link.get_attribute("href")
            if href and re.search(r'/events/\d+', href):
                fb_id = re.search(r'/events/(\d+)', href).group(1)
                name = link.inner_text().strip()
                events.append({
                    "fbId": fb_id,
                    "fbUrl": f"https://www.facebook.com/events/{fb_id}",
                    "name": name,
                    # Detailné polia by vyžadovali ďalší request na každý event
                })

        browser.close()

    return events
"""


def scrape_events_playwright(fb_page_id: str, proxy: str = None) -> list:
    # Wrapper funkcia – v produkcii by volala scrape_fb_page_playwright()
    # Tu iba ukážeme že rozhranie je rovnaké ako Apify verzia v main.py
    raise NotImplementedError(
        "Playwright scraper nie je aktívny v PoC verzii.\n"
        "Pre aktiváciu: pip install playwright && playwright install chromium\n"
        "A odkomentuj kód vyššie."
    )
