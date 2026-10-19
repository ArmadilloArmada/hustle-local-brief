from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from .cluster import cluster_events
from .draft import draft_artifacts
from .fetch import fetch_feeds


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError("Config root must be a mapping")
    return data


def run(config_path: Path, out_dir: Path | None = None) -> dict:
    config = load_config(config_path)
    tz = ZoneInfo(config.get("city", {}).get("timezone", "America/Chicago"))
    generated_at = datetime.now(tz)

    events = fetch_feeds(config)
    clusters = cluster_events(events)
    brief, social, mode = draft_artifacts(config, clusters, generated_at)

    dest = out_dir or Path(config.get("output", {}).get("dir") or "out")
    dest.mkdir(parents=True, exist_ok=True)

    brief_name = f"brief-{generated_at.strftime('%Y-%m-%d')}.md"
    brief_path = dest / brief_name
    social_path = dest / "social-posts.md"

    brief_path.write_text(brief, encoding="utf-8")
    social_path.write_text(social, encoding="utf-8")

    return {
        "events": len(events),
        "categories": len(clusters),
        "mode": mode,
        "brief": str(brief_path),
        "social": str(social_path),
    }
