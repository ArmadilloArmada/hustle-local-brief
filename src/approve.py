"""Human approval gate for draft brief + social posts.

Records an approval stamp under out/. Never posts anywhere.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


APPROVAL_FILENAME = ".approval.json"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def find_latest_brief(out_dir: Path) -> Path | None:
    briefs = sorted(out_dir.glob("brief-*.md"), key=lambda p: p.name)
    return briefs[-1] if briefs else None


def resolve_artifacts(
    out_dir: Path,
    brief: Path | None = None,
    social: Path | None = None,
) -> tuple[Path, Path]:
    brief_path = brief or find_latest_brief(out_dir)
    social_path = social or (out_dir / "social-posts.md")
    if brief_path is None or not brief_path.exists():
        raise FileNotFoundError(
            f"No brief-*.md found under {out_dir}. Run `python -m src` first."
        )
    if not social_path.exists():
        raise FileNotFoundError(
            f"Missing {social_path}. Run `python -m src` first."
        )
    return brief_path.resolve(), social_path.resolve()


def approval_path(out_dir: Path) -> Path:
    return out_dir / APPROVAL_FILENAME


def load_approval(out_dir: Path) -> dict | None:
    path = approval_path(out_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def write_approval(
    out_dir: Path,
    brief_path: Path,
    social_path: Path,
    *,
    note: str = "",
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = {
        "approved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "brief": brief_path.name,
        "social": social_path.name,
        "brief_sha256": _sha256(brief_path),
        "social_sha256": _sha256(social_path),
        "note": note.strip(),
        "auto_post": False,
        "reminder": (
            "Human pastes only — never auto-post to Facebook, Nextdoor, Discord, "
            "or any other channel."
        ),
    }
    path = approval_path(out_dir)
    path.write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")
    return path


def verify_approval(
    out_dir: Path,
    brief_path: Path,
    social_path: Path,
) -> tuple[bool, str]:
    """Return (ok, message). Fail if missing, mismatched, or files changed since approve."""
    stamp = load_approval(out_dir)
    if not stamp:
        return False, f"No approval stamp at {approval_path(out_dir)}. Run `python -m src approve` first."

    if stamp.get("brief") != brief_path.name or stamp.get("social") != social_path.name:
        return (
            False,
            "Approval stamp does not match current brief/social filenames. Re-run approve.",
        )

    if stamp.get("brief_sha256") != _sha256(brief_path):
        return False, f"{brief_path.name} changed since approval. Re-run approve after edits."
    if stamp.get("social_sha256") != _sha256(social_path):
        return False, f"{social_path.name} changed since approval. Re-run approve after edits."

    return True, f"Approved at {stamp.get('approved_at', '?')}"


def approve(
    out_dir: Path,
    *,
    brief: Path | None = None,
    social: Path | None = None,
    note: str = "",
    dry_run: bool = False,
) -> dict:
    brief_path, social_path = resolve_artifacts(out_dir, brief, social)

    preview = {
        "brief": str(brief_path),
        "social": str(social_path),
        "brief_bytes": brief_path.stat().st_size,
        "social_bytes": social_path.stat().st_size,
    }

    if dry_run:
        print("Dry-run approve — would stamp:", file=sys.stderr)
        print(f"  brief:  {brief_path}", file=sys.stderr)
        print(f"  social: {social_path}", file=sys.stderr)
        print("Nothing written. No posts sent.", file=sys.stderr)
        return {**preview, "dry_run": True, "approval": None}

    path = write_approval(out_dir, brief_path, social_path, note=note)
    return {**preview, "dry_run": False, "approval": str(path)}
