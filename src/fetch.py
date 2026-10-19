from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any, Optional
from zoneinfo import ZoneInfo

import feedparser
import requests
from icalendar import Calendar

from .models import Event

USER_AGENT = "HustleLocalBrief/0.1 (+https://github.com/armadilloarmada/hustle-local-brief; public RSS/iCal)"
TIMEOUT = 45


def _strip_html(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_dt(value: Any, tz: ZoneInfo) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=tz)
        return value
    if isinstance(value, str):
        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError):
            pass
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            return dt
        except ValueError:
            return None
    # feedparser time struct
    if hasattr(value, "tm_year"):
        try:
            return datetime(*value[:6], tzinfo=timezone.utc).astimezone(tz)
        except (TypeError, ValueError):
            return None
    return None


def fetch_url(url: str) -> bytes:
    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.content


def parse_rss(content: bytes, source: str, tz: ZoneInfo) -> list[Event]:
    parsed = feedparser.parse(content)
    events: list[Event] = []
    for entry in parsed.entries:
        title = _strip_html(getattr(entry, "title", "") or "Untitled")
        link = getattr(entry, "link", "") or ""
        summary = _strip_html(getattr(entry, "summary", "") or getattr(entry, "description", "") or "")
        starts = None
        for key in ("published_parsed", "updated_parsed"):
            starts = _parse_dt(getattr(entry, key, None), tz)
            if starts:
                break
        if starts is None:
            for key in ("published", "updated"):
                starts = _parse_dt(getattr(entry, key, None), tz)
                if starts:
                    break
        # xCal / Localist sometimes expose dc:date
        if starts is None and hasattr(entry, "dc_date"):
            starts = _parse_dt(entry.dc_date, tz)
        uid = getattr(entry, "id", "") or getattr(entry, "guid", "") or link or title
        location = ""
        if hasattr(entry, "location"):
            location = _strip_html(str(entry.location))
        events.append(
            Event(
                title=title,
                url=link,
                source=source,
                starts_at=starts,
                summary=summary[:500],
                location=location,
                uid=str(uid),
            )
        )
    return events


def parse_ical(content: bytes, source: str, tz: ZoneInfo, window_start: datetime, window_end: datetime) -> list[Event]:
    cal = Calendar.from_ical(content)
    events: list[Event] = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        title = _strip_html(str(component.get("summary") or "Untitled"))
        description = _strip_html(str(component.get("description") or ""))
        location = _strip_html(str(component.get("location") or ""))
        url = ""
        if component.get("url"):
            url = str(component.get("url"))
        uid = str(component.get("uid") or f"{title}|{component.get('dtstart')}")
        dtstart = component.get("dtstart")
        starts = None
        if dtstart is not None:
            raw = dtstart.dt
            if isinstance(raw, datetime):
                starts = raw if raw.tzinfo else raw.replace(tzinfo=tz)
            else:
                # all-day date
                starts = datetime(raw.year, raw.month, raw.day, tzinfo=tz)
        if starts is None:
            continue
        if starts < window_start or starts > window_end:
            continue
        events.append(
            Event(
                title=title,
                url=url,
                source=source,
                starts_at=starts,
                summary=description[:500],
                location=location,
                uid=uid,
            )
        )
    return events


def fetch_feeds(config: dict) -> list[Event]:
    tz_name = config.get("city", {}).get("timezone", "America/Chicago")
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    window_days = int(config.get("window_days", 7))
    # Include yesterday so late-night / timezone edges still show
    window_start = now - timedelta(days=1)
    window_end = now + timedelta(days=window_days)
    max_events = int(config.get("max_events", 80))

    collected: list[Event] = []
    errors: list[str] = []

    for feed in config.get("feeds", []):
        name = feed.get("name") or feed.get("url")
        url = feed["url"]
        ftype = (feed.get("type") or "rss").lower()
        try:
            content = fetch_url(url)
            if ftype in ("rss", "atom", "xml"):
                items = parse_rss(content, name, tz)
                # Prefer items inside window when dates exist; keep undated if few dated
                dated = [e for e in items if e.starts_at and window_start <= e.starts_at <= window_end]
                undated = [e for e in items if e.starts_at is None]
                kept = dated if dated else items[:40]
                # sprinkle a few undated if we have room
                if dated and undated:
                    kept = dated + undated[:5]
                collected.extend(kept)
            elif ftype in ("ical", "ics"):
                collected.extend(parse_ical(content, name, tz, window_start, window_end))
            else:
                errors.append(f"Unknown feed type '{ftype}' for {name}")
        except Exception as exc:  # noqa: BLE001 — surface per-feed failures, keep going
            errors.append(f"{name}: {exc}")

    # Dedupe
    seen: set[str] = set()
    unique: list[Event] = []
    for event in collected:
        key = event.dedupe_key()
        if key in seen:
            continue
        seen.add(key)
        unique.append(event)

    unique.sort(key=lambda e: (e.starts_at or datetime.max.replace(tzinfo=tz), e.title.lower()))
    if len(unique) > max_events:
        unique = unique[:max_events]

    if errors:
        print("Feed warnings:")
        for err in errors:
            print(f"  - {err}")

    return unique
