from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .approve import approve
from .export import export_pack
from .pipeline import run


def _add_out_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("out"),
        help="Draft output directory (default: ./out)",
    )


def _add_artifact_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--brief",
        type=Path,
        default=None,
        help="Specific brief-*.md (default: latest under out/)",
    )
    parser.add_argument(
        "--social",
        type=Path,
        default=None,
        help="Social posts file (default: out/social-posts.md)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src",
        description=(
            "Austin weekly community brief: draft → human approve → export paste pack. "
            "Never auto-posts to Facebook, Nextdoor, Discord, or anywhere else."
        ),
    )
    sub = parser.add_subparsers(dest="command")

    # Default / draft (also the bare `python -m src` path)
    draft = sub.add_parser(
        "draft",
        help="Fetch feeds, cluster, write out/brief-*.md + out/social-posts.md",
    )
    draft.add_argument(
        "-c",
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to config.yaml (default: ./config.yaml)",
    )
    draft.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="Output directory (default: from config, usually out/)",
    )

    ap = sub.add_parser(
        "approve",
        help="Stamp human approval for the latest brief + social posts (no posting)",
    )
    _add_out_arg(ap)
    _add_artifact_args(ap)
    ap.add_argument(
        "--note",
        default="",
        help="Optional note stored on the approval stamp",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be approved without writing the stamp",
    )

    ex = sub.add_parser(
        "export",
        help="Write out/export/ ready-to-paste pack (requires prior approve)",
    )
    _add_out_arg(ex)
    _add_artifact_args(ex)
    ex.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="Export directory (default: out/export)",
    )
    ex.add_argument(
        "--no-pdf",
        action="store_true",
        help="Skip brief.pdf (Markdown + social copy files only)",
    )
    ex.add_argument(
        "--force",
        action="store_true",
        help="Export even without a matching approval stamp (not recommended)",
    )
    ex.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be exported without writing files",
    )

    return parser


def _cmd_draft(args: argparse.Namespace) -> int:
    if not args.config.exists():
        example = Path("config.example.yaml")
        hint = (
            f"Missing {args.config}. Copy config.example.yaml → config.yaml and retry."
            if example.exists()
            else f"Missing {args.config}."
        )
        print(hint, file=sys.stderr)
        return 1

    result = run(args.config, args.out)
    print(
        f"Drafted {result['events']} events across {result['categories']} categories "
        f"({result['mode']} mode)."
    )
    print(f"  brief:  {result['brief']}")
    print(f"  social: {result['social']}")
    print("Next: review → `python -m src approve` → `python -m src export` → human pastes.")
    print("Human review required — nothing was posted.")
    return 0


def _cmd_approve(args: argparse.Namespace) -> int:
    try:
        result = approve(
            args.out,
            brief=args.brief,
            social=args.social,
            note=args.note,
            dry_run=args.dry_run,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if result.get("dry_run"):
        return 0

    print("Approved (human stamp only — nothing posted).")
    print(f"  brief:    {result['brief']}")
    print(f"  social:   {result['social']}")
    print(f"  stamp:    {result['approval']}")
    print("Next: `python -m src export` then paste files from out/export/ yourself.")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    try:
        result = export_pack(
            args.out,
            brief=args.brief,
            social=args.social,
            dest=args.dest,
            pdf=not args.no_pdf,
            require_approval=not args.force,
            dry_run=args.dry_run,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except PermissionError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if result.get("dry_run"):
        return 0

    print("Export pack ready — human paste only (no auto-post).")
    print(f"  dir: {result['export_dir']}")
    for name in result["files"]:
        print(f"  - {name}")
    print("Open out/export/ and paste into Facebook / Nextdoor / Discord yourself.")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()

    # Bare `python -m src` (no subcommand) keeps drafting for backward compatibility.
    if not argv:
        argv = ["draft"]
    elif argv[0] not in ("-h", "--help") and argv[0].startswith("-"):
        argv = ["draft", *argv]

    args = parser.parse_args(argv)
    if args.command == "draft":
        return _cmd_draft(args)
    if args.command == "approve":
        return _cmd_approve(args)
    if args.command == "export":
        return _cmd_export(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
