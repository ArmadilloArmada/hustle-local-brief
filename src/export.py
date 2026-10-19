"""Export an approved pack to out/export/ for human paste.

Never posts to Facebook, Nextdoor, Discord, or any other channel.
"""

from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from .approve import resolve_artifacts, verify_approval


EXPORT_SUBDIR = "export"

# Map social-posts.md ## headings → paste filenames
_SECTION_FILES = (
    (("community post", "community"), "community-post.txt"),
    (("short post", "short"), "short-post.txt"),
    (("discord", "slack", "discord / slack", "discord/slack"), "discord-blurb.txt"),
)


def _strip_md_noise(text: str) -> str:
    """Light cleanup so paste targets get mostly plain copy."""
    lines = []
    for line in text.splitlines():
        # Drop heading markers left over from extraction
        if line.startswith("#"):
            continue
        lines.append(line)
    body = "\n".join(lines).strip()
    # Collapse 3+ blank lines
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body + ("\n" if body else "")


def split_social_sections(social_md: str) -> dict[str, str]:
    """Split social-posts.md on ## headings into paste-ready files."""
    parts: dict[str, list[str]] = {}
    current: str | None = None
    for line in social_md.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip().lower()
            current = None
            for aliases, filename in _SECTION_FILES:
                if any(alias in heading for alias in aliases):
                    current = filename
                    parts.setdefault(current, [])
                    break
            continue
        if current is not None:
            parts[current].append(line)

    return {name: _strip_md_noise("\n".join(lines)) for name, lines in parts.items()}


def _simple_pdf(text: str, dest: Path, title: str = "Local Brief") -> None:
    """Write a minimal single-page-stream PDF from plain text (stdlib only)."""
    # Escape PDF string specials
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    # Keep ASCII-ish for the built-in Helvetica font
    clean_lines: list[str] = []
    for raw in text.splitlines():
        line = raw.encode("ascii", "replace").decode("ascii")
        # Soft-wrap long lines
        while len(line) > 95:
            clean_lines.append(line[:95])
            line = line[95:]
        clean_lines.append(line)

    # Cap pages of content to keep the stream small (~60 lines / page worth)
    max_lines = 240
    if len(clean_lines) > max_lines:
        clean_lines = clean_lines[:max_lines] + ["", "...(truncated for PDF; see brief.md)"]

    y_start = 770
    leading = 11
    content_ops = [f"BT /F1 10 Tf 40 {y_start} Td {leading} TL"]
    content_ops.append(f"({esc(title[:80])}) Tj T*")
    content_ops.append("T*")
    for line in clean_lines:
        content_ops.append(f"({esc(line)}) Tj T*")
    content_ops.append("ET")
    stream = "\n".join(content_ops).encode("latin-1", "replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n"
    )
    objects.append(
        f"4 0 obj<< /Length {len(stream)} >>stream\n".encode("ascii")
        + stream
        + b"\nendstream\nendobj\n"
    )
    objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    out.extend(
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode(
            "ascii"
        )
    )
    dest.write_bytes(bytes(out))


def _pack_readme(brief_name: str, files: list[str]) -> str:
    listed = "\n".join(f"  - {name}" for name in files)
    return f"""# Ready-to-paste export pack

Approved brief: {brief_name}
Exported (UTC): {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}

## Workflow

1. Approve drafts (`python -m src approve`)
2. Export this pack (`python -m src export`)
3. Human pastes — open the files below and copy into Facebook / Nextdoor / Discord yourself

This tool never auto-posts.

## Files

{listed}

Tips:
- Prefer `community-post.txt`, `short-post.txt`, and `discord-blurb.txt` for channel paste.
- Use `brief.md` (or `brief.pdf`) as the one-pager / link target.
- Re-verify times and venues on source links before sharing.
"""


def export_pack(
    out_dir: Path,
    *,
    brief: Path | None = None,
    social: Path | None = None,
    dest: Path | None = None,
    pdf: bool = True,
    require_approval: bool = True,
    dry_run: bool = False,
) -> dict:
    brief_path, social_path = resolve_artifacts(out_dir, brief, social)

    if require_approval:
        ok, msg = verify_approval(out_dir, brief_path, social_path)
        if not ok:
            raise PermissionError(msg)

    export_dir = dest or (out_dir / EXPORT_SUBDIR)
    social_text = social_path.read_text(encoding="utf-8")
    brief_text = brief_path.read_text(encoding="utf-8")
    sections = split_social_sections(social_text)

    planned: list[str] = [
        "README.md",
        "brief.md",
        "social-posts.md",
    ]
    if pdf:
        planned.append("brief.pdf")
    for name in ("community-post.txt", "short-post.txt", "discord-blurb.txt"):
        if name in sections and sections[name].strip():
            planned.append(name)
        elif name not in sections:
            # still plan empty stubs so the pack shape is stable
            planned.append(name)

    if dry_run:
        print("Dry-run export — would write:", file=sys.stderr)
        print(f"  dest: {export_dir}", file=sys.stderr)
        for name in planned:
            print(f"  - {name}", file=sys.stderr)
        print("Nothing written. No posts sent.", file=sys.stderr)
        return {
            "dry_run": True,
            "export_dir": str(export_dir),
            "files": planned,
            "brief": str(brief_path),
            "social": str(social_path),
        }

    if export_dir.exists():
        # Replace previous pack so humans always paste the latest approved set
        for child in export_dir.iterdir():
            if child.name == ".gitkeep":
                continue
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / ".gitkeep").touch()

    written: list[str] = []

    (export_dir / "brief.md").write_text(brief_text, encoding="utf-8")
    written.append("brief.md")

    shutil.copy2(social_path, export_dir / "social-posts.md")
    written.append("social-posts.md")

    for name in ("community-post.txt", "short-post.txt", "discord-blurb.txt"):
        body = sections.get(name, "").strip()
        if not body:
            body = (
                f"(No '{name}' section found in {social_path.name}. "
                "Edit social-posts.md, re-approve, and export again.)"
            )
        (export_dir / name).write_text(body + "\n", encoding="utf-8")
        written.append(name)

    if pdf:
        pdf_path = export_dir / "brief.pdf"
        # Prefer plain-ish text for the minimal PDF writer
        plain = re.sub(r"[#*_`]", "", brief_text)
        _simple_pdf(plain, pdf_path, title=brief_path.stem.replace("-", " ").title())
        written.append("brief.pdf")

    readme = _pack_readme(brief_path.name, written)
    (export_dir / "README.md").write_text(readme, encoding="utf-8")
    written.insert(0, "README.md")

    return {
        "dry_run": False,
        "export_dir": str(export_dir),
        "files": written,
        "brief": str(brief_path),
        "social": str(social_path),
    }
