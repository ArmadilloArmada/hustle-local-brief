from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from .models import Cluster, Event


def _fmt_when(event: Event, tz: ZoneInfo) -> str:
    if not event.starts_at:
        return "Date TBA"
    local = event.starts_at.astimezone(tz)
    # Portable (no %-d / %-I) for Linux + Windows
    day = local.strftime("%a %b ") + str(local.day)
    hour = local.hour % 12 or 12
    ampm = "AM" if local.hour < 12 else "PM"
    return f"{day} · {hour}:{local.minute:02d} {ampm}"


def _bullet(event: Event, tz: ZoneInfo) -> str:
    when = _fmt_when(event, tz)
    loc = f" @ {event.location}" if event.location else ""
    link = f" — {event.url}" if event.url else ""
    return f"- **{event.title}** ({when}{loc}){link}"


def template_brief(
    city: str,
    region: str,
    clusters: list[Cluster],
    generated_at: datetime,
    tz: ZoneInfo,
) -> str:
    date_label = generated_at.strftime("%Y-%m-%d")
    lines = [
        f"# What's new in {city}, {region} — week of {date_label}",
        "",
        f"_Draft generated {generated_at.astimezone(tz).strftime('%Y-%m-%d %H:%M %Z')} "
        f"(template mode — no OPENAI_API_KEY). Review before sharing._",
        "",
        f"A quick scan of public calendars around {city}: library programs, campus events, "
        "and other free community listings. Verify times/locations on the source links.",
        "",
    ]
    if not clusters:
        lines.append("_No events found in the configured window. Check feed URLs or widen `window_days`._")
        lines.append("")
        return "\n".join(lines)

    for cluster in clusters:
        heading = cluster.category.replace("_", " ").title()
        lines.append(f"## {heading} ({cluster.count})")
        lines.append("")
        for event in cluster.events[:12]:
            lines.append(_bullet(event, tz))
        if cluster.count > 12:
            lines.append(f"- _…plus {cluster.count - 12} more in this category_")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "**Sources:** public RSS/iCal feeds listed in `config.yaml`. "
            "This tool never auto-posts — paste after a human edit.",
            "",
        ]
    )
    return "\n".join(lines)


def template_social(city: str, clusters: list[Cluster], tz: ZoneInfo) -> str:
    lines = [
        "# Social post drafts (human approve — do not auto-post)",
        "",
    ]
    highlights: list[Event] = []
    for cluster in clusters:
        highlights.extend(cluster.events[:2])
    highlights = highlights[:6]

    # Short Nextdoor / Facebook style
    lines.append("## Community post")
    lines.append("")
    lines.append(f"What's new in {city} this week:")
    lines.append("")
    if highlights:
        for event in highlights[:5]:
            when = _fmt_when(event, tz)
            lines.append(f"• {event.title} — {when}")
        lines.append("")
        lines.append("Full list + links in comments / this week's brief.")
    else:
        lines.append("(No highlights yet — re-run after feeds return events.)")
    lines.append("")

    # X / short
    lines.append("## Short post")
    lines.append("")
    if highlights:
        top = highlights[0]
        lines.append(
            f"{city} this week: {top.title} ({_fmt_when(top, tz)}). "
            f"More community picks in the weekly brief."
        )
    else:
        lines.append(f"{city} weekly brief is cooking — check back after the next fetch.")
    lines.append("")

    # Discord / Slack style
    lines.append("## Discord / Slack blurb")
    lines.append("")
    lines.append(f"**{city} weekly brief** — top categories:")
    for cluster in clusters[:5]:
        sample = cluster.events[0].title if cluster.events else "—"
        lines.append(f"- {cluster.category}: {cluster.count} listings (e.g. {sample})")
    lines.append("")
    lines.append("_Edit voice + verify facts before posting. No auto-publish._")
    lines.append("")
    return "\n".join(lines)


def _clusters_payload(clusters: list[Cluster], tz: ZoneInfo) -> list[dict]:
    payload = []
    for cluster in clusters:
        payload.append(
            {
                "category": cluster.category,
                "events": [
                    {
                        "title": e.title,
                        "when": _fmt_when(e, tz),
                        "location": e.location,
                        "url": e.url,
                        "summary": e.summary[:240],
                        "source": e.source,
                    }
                    for e in cluster.events[:15]
                ],
            }
        )
    return payload


def openai_draft(
    city: str,
    region: str,
    clusters: list[Cluster],
    generated_at: datetime,
    tz: ZoneInfo,
    model: str,
) -> Optional[tuple[str, str]]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        print("openai package missing; falling back to template draft.")
        return None

    client = OpenAI(api_key=api_key)
    payload = {
        "city": city,
        "region": region,
        "generated_at": generated_at.isoformat(),
        "clusters": _clusters_payload(clusters, tz),
    }
    system = (
        "You draft a friendly local community weekly brief for Austin, TX. "
        "Use only the provided events — do not invent venues, times, or prices. "
        "Return JSON with keys brief_markdown and social_markdown. "
        "brief_markdown: one-pager with intro + category sections + source caveat. "
        "social_markdown: Community post, Short post, and Discord/Slack blurb sections. "
        "Never claim you posted anywhere. Keep tone warm and practical."
    )
    user = (
        "Draft from this JSON event clusters. Prefer the most distinctive listings; "
        "skip dull duplicates. Include links when present.\n\n"
        + json.dumps(payload, ensure_ascii=False)[:120000]
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0.4,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        brief = (data.get("brief_markdown") or "").strip()
        social = (data.get("social_markdown") or "").strip()
        if not brief or not social:
            return None
        note = (
            f"\n\n---\n_LLM draft via `{model}` at "
            f"{generated_at.astimezone(tz).strftime('%Y-%m-%d %H:%M %Z')}. Human edit required._\n"
        )
        return brief + note, social + note
    except Exception as exc:  # noqa: BLE001
        print(f"OpenAI draft failed ({exc}); using template.")
        return None


def draft_artifacts(
    config: dict,
    clusters: list[Cluster],
    generated_at: datetime,
) -> tuple[str, str, str]:
    city = config.get("city", {}).get("name", "Austin")
    region = config.get("city", {}).get("region", "TX")
    tz = ZoneInfo(config.get("city", {}).get("timezone", "America/Chicago"))
    openai_cfg = config.get("openai") or {}
    mode = "template"

    brief = social = None
    if openai_cfg.get("enabled", True):
        result = openai_draft(
            city,
            region,
            clusters,
            generated_at,
            tz,
            model=str(openai_cfg.get("model") or "gpt-4o-mini"),
        )
        if result:
            brief, social = result
            mode = "openai"

    if brief is None or social is None:
        brief = template_brief(city, region, clusters, generated_at, tz)
        social = template_social(city, clusters, tz)
        mode = "template"

    return brief, social, mode
