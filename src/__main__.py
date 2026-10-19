from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src",
        description="Fetch Austin public event feeds, cluster by category, draft weekly brief + social posts.",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to config.yaml (default: ./config.yaml)",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="Output directory (default: from config, usually out/)",
    )
    args = parser.parse_args(argv)

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
    print("Human review required — nothing was posted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
