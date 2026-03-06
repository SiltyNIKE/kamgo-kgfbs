# AI kategorizácia eventov do Kamgo stromu kategórií cez OpenRouter API.

import os
import requests

KAMGO_CATEGORIES = [
    "Pre deti", "Mládež", "Hudba", "Pohyb a šport",
    "Kultúra a umenie", "Vzdelávanie", "Zábava", "Gastro",
    "Príroda a cestovanie", "Biznis a networking", "Iné"
]

SYSTEM_PROMPT = (
    "You are an expert at categorizing cultural and social events in Slovakia.\n"
    "You will receive an event name and description. Your task is to assign it to exactly one of these categories:\n\n"
    + "\n".join(f"- {c}" for c in KAMGO_CATEGORIES)
    + "\n\nRespond with ONLY the category name from the list above. Nothing else.\n"
    "If you are unsure, use \"Iné\"."
)


def categorize_event(event: dict) -> str:
    # Step 1: try to categorize from FB tags – fast and free
    quick = _quick_categorize_from_tags(event.get("category", "") or "")
    if quick:
        return quick

    # Step 2: fall back to AI if tags are not sufficient
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "Iné"

    return _ai_categorize(
        name=event.get("name", ""),
        description=event.get("description", ""),
        api_key=api_key
    )


def _quick_categorize_from_tags(tags_str: str) -> str | None:
    mapping = {
        "music": "Hudba", "concert": "Hudba", "hudba": "Hudba",
        "sport": "Pohyb a šport", "fitness": "Pohyb a šport",
        "children": "Pre deti", "kids": "Pre deti", "deti": "Pre deti",
        "youth": "Mládež", "mládež": "Mládež",
        "art": "Kultúra a umenie", "gallery": "Kultúra a umenie",
        "education": "Vzdelávanie", "workshop": "Vzdelávanie",
        "food": "Gastro", "wine": "Gastro",
        "business": "Biznis a networking",
    }
    tags_lower = tags_str.lower()
    for keyword, category in mapping.items():
        if keyword in tags_lower:
            return category
    return None


def _ai_categorize(name: str, description: str, api_key: str) -> str:
    user_prompt = f"Názov eventu: {name}\nPopis: {description[:500]}"

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "anthropic/claude-haiku",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 20
            },
            timeout=10
        )
        result = resp.json()["choices"][0]["message"]["content"].strip()
        return result if result in KAMGO_CATEGORIES else "Iné"

    except Exception as e:
        # Log the error so monitoring can catch expired credits, invalid keys, etc.
        print(f"ERROR: AI categorization failed for '{name[:50]}': {type(e).__name__}: {e}")
        return "Iné"
