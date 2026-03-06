# Mapovanie FB eventu na Kamgo Event schému.
# Vstup: raw dáta z Apify scrapera + subjekt z Kamgo API

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# FB events use local Slovakia time – we localize and convert to UTC
_LOCAL_TZ = ZoneInfo("Europe/Bratislava")

FALLBACK_CITY = "Unknown location (GPS coordinates – reverse geocoding needed)"
FALLBACK_DESCRIPTION = "No description available"

# aiCategory is internal pipeline field, must not reach Kamgo API
_INTERNAL_FIELDS = {"aiCategory"}


def map_fb_event_to_kamgo(fb_event: dict, subject: dict) -> dict:
    return {
        "fbId": str(fb_event.get("fbId") or ""),
        "fbUrl": fb_event.get("fbUrl"),
        # (... or "") handles the case where Apify returns null instead of missing key
        "name": (fb_event.get("name") or "").strip(),
        "description": (fb_event.get("description") or "").strip() or FALLBACK_DESCRIPTION,
        "placeName": (fb_event.get("placeName") or "").strip() or "Neznáme miesto",
        "city": _extract_city(fb_event),
        "street": _extract_street(fb_event),
        "zipCode": fb_event.get("zipCode"),
        "startAt": parse_datetime(fb_event.get("startAt")),
        "finishAt": parse_datetime(fb_event.get("finishAt")),
        "scrappedAt": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "imageUrl": fb_event.get("imageUrl"),
        "category": ";".join(fb_event.get("tags", [])) or None,
        "aiCategory": None,  # filled by main.py after categorization, removed before API call
        "ticketUrl": fb_event.get("ticketUrl"),
        "subjectKamgoId": subject.get("kamgoId"),
        "subjectKamgoType": subject.get("type") or subject.get("venue", "venue"),
    }


def prepare_for_api(event: dict) -> dict:
    # Merge aiCategory into category, remove internal fields, strip None values.
    api_event = dict(event)

    ai_category = api_event.pop("aiCategory", None)
    if ai_category:
        original = api_event.get("category") or ""
        api_event["category"] = ";".join(filter(None, [ai_category, original])) or None

    for field in _INTERNAL_FIELDS - {"aiCategory"}:
        api_event.pop(field, None)

    return {k: v for k, v in api_event.items() if v is not None}


def _extract_city(fb_event: dict) -> str:
    city = fb_event.get("city", "")
    if not city or _is_coordinates(city):
        # TODO: reverse geocoding (e.g. Google Maps API)
        return FALLBACK_CITY
    return city


def _extract_street(fb_event: dict) -> str:
    street = fb_event.get("street") or ""
    return "" if _is_coordinates(street) else street


def _is_coordinates(value: str) -> bool:
    import re
    return bool(re.match(r'^-?\d+\.\d+,\s*-?\d+\.\d+$', value.strip()))


def parse_datetime(value) -> str | None:
    # Output format per Kamgo Swagger: "YYYY-MM-DD HH:MM" (UTC)
    # Naive strings from Apify are treated as Europe/Bratislava local time.
    if not value:
        return None
    if isinstance(value, str):
        aware_str = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(aware_str)
            if dt.tzinfo is not None:
                return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass
        try:
            naive_dt = datetime.fromisoformat(value)
            return naive_dt.replace(tzinfo=_LOCAL_TZ).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    return str(value)
