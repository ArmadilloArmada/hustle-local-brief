from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


CATEGORIES = (
    "family",
    "arts",
    "music",
    "outdoors",
    "civic",
    "learning",
    "food",
    "tech",
    "other",
)

# Localist RSS titles often look like "Oct 19, 2026: Event Name at Venue"
_TITLE_PREFIX = re.compile(
    r"^(?:[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}:\s+)",
)


@dataclass
class Event:
    title: str
    url: str
    source: str
    starts_at: Optional[datetime] = None
    summary: str = ""
    location: str = ""
    category: str = "other"
    uid: str = ""

    def dedupe_key(self) -> str:
        """Collapse RSS/iCal duplicates of the same listing."""
        title = _TITLE_PREFIX.sub("", (self.title or "").strip()).lower()
        title = re.sub(r"\s+", " ", title)
        day = self.starts_at.date().isoformat() if self.starts_at else ""
        if title and day:
            return f"{title}|{day}"
        if self.uid:
            return self.uid.lower().strip()
        return f"{title}|{self.url}|{day}"


@dataclass
class Cluster:
    category: str
    events: list[Event] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.events)
