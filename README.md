# hustle-local-brief

Austin, TX weekly **"what's new"** community brief — a small Python CLI that pulls **public** event RSS/iCal feeds, clusters listings by category, and drafts a one-pager plus social copy for **human approval**.

Part of [Project Hustle](https://github.com/armadilloarmada) Tier 0 (local community briefs). **No auto-posting** to Nextdoor, Facebook, Discord, or anywhere else.

## Workflow

```
Draft → Approve → Export → human pastes
```

| Step | Command | Result |
|------|---------|--------|
| 1. Draft | `python -m src` | `out/brief-YYYY-MM-DD.md`, `out/social-posts.md` |
| 2. Approve | `python -m src approve` | Human stamp at `out/.approval.json` (no network posts) |
| 3. Export | `python -m src export` | Ready-to-paste pack under `out/export/` |
| 4. Paste | *(you)* | Copy files into Facebook / Nextdoor / Discord yourself |

This tool **never** posts to social platforms automatically.

## Requirements

- Python **3.11+**
- Network access to the public feeds in your config
- Optional: `OPENAI_API_KEY` for LLM drafting (otherwise a deterministic template draft is written)

## Quick start

```bash
git clone https://github.com/armadilloarmada/hustle-local-brief.git
cd hustle-local-brief
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
python -m src
```

Review the drafts, then:

```bash
python -m src approve
python -m src export
```

Open `out/export/` and paste:

- `brief.md` (or `brief.pdf`) — weekly one-pager
- `community-post.txt` — Nextdoor / Facebook-style copy
- `short-post.txt` — short / X-style copy
- `discord-blurb.txt` — Discord / Slack blurb
- `social-posts.md` — full social draft for reference
- `README.md` — pack checklist

### Dry-run (no writes)

```bash
python -m src approve --dry-run
python -m src export --dry-run
```

### Useful flags

```bash
python -m src approve --brief out/brief-2026-10-18.md --note "spot-checked APL times"
python -m src export --no-pdf          # Markdown + social files only
python -m src export --force           # skip approval gate (not recommended)
```

## Config

`config.example.yaml` ships with Austin-focused, ToS-safe public feeds:

| Feed | Type | Notes |
|------|------|--------|
| [Austin Public Library events](https://library.austintexas.gov/events-feed.xml) | RSS | Official APL feed (also listed on data.austintexas.gov) |
| [UT Austin / Texas Today](https://calendar.utexas.edu/calendar.xml) | RSS | Public Localist RSS |
| [UT Austin calendar](https://calendar.utexas.edu/calendar.ics) | iCal | Same calendar; pipeline keeps events inside `window_days` |

Add or remove entries under `feeds:`. Supported `type` values: `rss`, `ical`.

## Optional OpenAI drafting

```bash
export OPENAI_API_KEY=sk-...
python -m src
```

If the key is unset, the draft fails, or `openai.enabled` is false, the CLI falls back to the template writer so dry-runs stay free.

## Pipeline

```
config.yaml → fetch RSS/iCal → cluster by category → draft brief + social → out/
         → human approve → out/export/ paste pack → human posts manually
```

Categories (keyword heuristics): family, arts, music, outdoors, civic, learning, food, tech, other.

## Weekly schedule (GitHub Actions)

Every Monday at **14:10 UTC**, [`.github/workflows/weekly-local-brief.yml`](.github/workflows/weekly-local-brief.yml) runs a **draft-only** pipeline (`python -m src`) and uploads artifact **`local-brief-draft`** (no approve/export/post). Download from the Actions run → **Artifacts**, unzip into `out/`, then approve + export locally.

## Compliance notes

- Prefer **official public RSS/iCal** endpoints; do not scrape sites that forbid it.
- Always verify times and venues before publishing — feeds can be stale or incomplete.
- Human posts only; automated posting risks platform bans and trust damage.

## License

MIT — see [`LICENSE`](LICENSE).
