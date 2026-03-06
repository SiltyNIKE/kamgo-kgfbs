# KGFBS – Kamgo Facebook Sourcing (Proof of Concept)

> ⚠️ **Disclaimer:** Tento repozitár obsahuje proof-of-concept architektúru a ukážkový kód.
> Reálny scraping Facebooku vyžaduje platený scraping service (napr. Apify) kvôli anti-bot ochrane FB.
> Skript demonštruje logiku spracovania dát, mapovania na Event schému a odosielania do Kamgo API.

## Architektúra

```
[Kamgo Subjects API] → [Scraping Layer] → [Data Mapper] → [AI Kategorizer] → [Kamgo API]
```

### Scraping Layer (3 možnosti)
1. **Apify** (odporúčané) – spoľahlivé, ~$50-100/mes pre 4000 stránok
2. **Playwright + proxies** – lacnejšie (~$20-40/mes), vyžaduje údržbu
3. **Facebook Graph API** – oficiálne, ale veľmi obmedzené pre verejné eventy

## Spustenie

```bash
pip install requests python-dotenv
python main.py --mode mock    # ukážka s mock dátami
python main.py --mode live    # vyžaduje Apify API key
```

## Štruktúra
- `main.py` – hlavný skript
- `mapper.py` – mapovanie FB eventu na Kamgo Event schému  
- `categorizer.py` – AI kategorizácia cez OpenRouter/Claude
- `dedup.py` – logika detekcie duplikátov
