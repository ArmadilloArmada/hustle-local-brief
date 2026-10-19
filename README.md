# hustle-local-brief

Austin, TX weekly **"what's new"** community brief — a small Python CLI that pulls **public** event RSS/iCal feeds, clusters listings by category, and drafts a one-pager plus social copy for **human approval**.

Part of [Project Hustle](https://github.com/armadilloarmada) Tier 0 (local community briefs). **No auto-posting** to Nextdoor, Facebook, Discord, or anywhere else.

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

Outputs (gitignored contents except `.gitkeep`):

- `out/brief-YYYY-MM-DD.md` — weekly brief draft
- `out/social-posts.md` — community / short / Discord-style post drafts

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
```

Categories (keyword heuristics): family, arts, music, outdoors, civic, learning, food, tech, other.

## Compliance notes

- Prefer **official public RSS/iCal** endpoints; do not scrape sites that forbid it.
- Always verify times and venues before publishing — feeds can be stale or incomplete.
- Human posts only; automated posting risks platform bans and trust damage.

## License

MIT — see [`LICENSE`](LICENSE).
