from __future__ import annotations

import re
from collections import defaultdict

from .models import CATEGORIES, Cluster, Event

# Keyword heuristics → category
RULES: list[tuple[str, tuple[str, ...]]] = [
    (
        "family",
        (
            "storytime",
            "story time",
            "kids",
            "children",
            "family",
            "toddler",
            "youth",
            "teen",
            "playgroup",
            "baby",
        ),
    ),
    (
        "music",
        ("concert", "music", "jazz", "band", "choir", "symphony", "opera", "live music", "song"),
    ),
    (
        "arts",
        (
            "art",
            "exhibit",
            "gallery",
            "theatre",
            "theater",
            "dance",
            "film",
            "museum",
            "choreograph",
            "visual",
        ),
    ),
    (
        "outdoors",
        ("park", "hike", "trail", "outdoor", "garden", "nature", "run ", "race", "bike", "paddle"),
    ),
    (
        "civic",
        (
            "council",
            "city hall",
            "board of",
            "public hearing",
            "town hall",
            "election",
            "zoning",
            "commission",
            "meeting",
        ),
    ),
    (
        "learning",
        (
            "workshop",
            "class",
            "lecture",
            "seminar",
            "library",
            "course",
            "talk time",
            "tutorial",
            "book club",
            "language",
        ),
    ),
    (
        "food",
        ("food", "farmers market", "market", "tasting", "culinary", "barbecue", "bbq", "brew"),
    ),
    (
        "tech",
        ("tech", "startup", "hack", "coding", "developer", "ai ", "software", "ux ", "product"),
    ),
]


def categorize(event: Event) -> str:
    blob = " ".join(
        [
            event.title or "",
            event.summary or "",
            event.location or "",
            event.source or "",
        ]
    ).lower()
    for category, keywords in RULES:
        for kw in keywords:
            if kw in blob:
                return category
    # light punctuation-insensitive fallback
    tokens = set(re.findall(r"[a-z0-9]+", blob))
    if "park" in tokens:
        return "outdoors"
    return "other"


def cluster_events(events: list[Event]) -> list[Cluster]:
    buckets: dict[str, list[Event]] = defaultdict(list)
    for event in events:
        event.category = categorize(event)
        buckets[event.category].append(event)

    clusters: list[Cluster] = []
    for category in CATEGORIES:
        items = buckets.get(category) or []
        if items:
            clusters.append(Cluster(category=category, events=items))
    # any unexpected categories
    for category, items in buckets.items():
        if category not in CATEGORIES and items:
            clusters.append(Cluster(category=category, events=items))
    return clusters
