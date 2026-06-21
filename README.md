# The Ledger

An independent, self-hosted tracker of confirmed U.S. police-misconduct
settlements: wrongful deaths, wrongful shootings, wrongful convictions, and
failures to provide care in custody. It shows recent entries, the largest
payouts on record, and two running totals — paid this year, and paid
all-time across every case in the ledger.

It is **not** a Claude/Anthropic product, doesn't call any Anthropic API,
and has no branding tying it back to this conversation. Once you deploy it,
it's yours and it runs on your own infrastructure.

## What's in this folder

| File | Purpose |
|---|---|
| `index.html` | The site itself. Pure HTML/CSS/JS, no build step, no framework. |
| `data.json` | The confirmed, public ledger — what powers the counters and lists. |
| `pending.json` | Candidates the crawler found but nobody has verified yet. |
| `scraper.py` | The crawler. Stdlib-only Python — no `pip install` required. |
| `.github/workflows/update-data.yml` | The cron job that runs the crawler every 12 hours. |

## Deploying it (free, ~5 minutes)

1. Create a new **public** GitHub repo and push this folder to it.
2. In the repo, go to **Settings → Pages**, set source to the `main`
   branch, root folder. GitHub will give you a URL like
   `https://yourname.github.io/the-ledger/`.
3. That's it. The workflow in `.github/workflows/update-data.yml` is
   already configured to run on GitHub's own scheduler — every 12 hours it
   checks public news for new settlement coverage, and if it finds anything
   it commits straight to your repo. GitHub Pages picks up the change
   automatically. No server, no API key, nothing to keep running on your
   own machine.

If you'd rather host it elsewhere (Netlify, Vercel, your own server,
literally a USB stick), `index.html` works anywhere — it tries to `fetch`
`data.json`/`pending.json` next to it, and falls back to an inlined
snapshot if those aren't reachable (e.g. opened directly as a local file).

## How the auto-refresh actually works

`scraper.py` searches Google News' public RSS feed (no API key needed) for
headlines that mention both a police-related keyword and a settlement-related
keyword, pulls out a dollar figure with a regex, and — if it isn't already
known — appends it to `pending.json` with status `needs_review`.

It intentionally **does not** write to `data.json`. Headline figures are
often rounded, sometimes describe a *proposed* settlement that later
changed, and occasionally are just wrong. A wrong dollar amount attached to
a real person's name is worse than a slower update, so nothing reaches the
public totals without a human checking it against a primary source first
(city council minutes, court docket, or a named outlet's reporting).

### Promoting a verified entry

Once you've checked a `pending.json` entry against a real source, move it
into `data.json` by hand, following the existing schema:

```json
{
  "id": "lastname-year",
  "name": "Full name",
  "location": "City, ST",
  "amount": 1234567,
  "date": "2026-01-01",
  "category": "Wrongful Death | Wrongful Shooting | Wrongful Conviction | Failure to Provide Care",
  "summary": "One or two factual sentences, no editorializing.",
  "source_name": "Outlet name",
  "source_url": "https://..."
}
```

Then delete it from `pending.json`. Commit, push, done — the live counters
recompute automatically from whatever is in `data.json`.

## Honest limitations

- The crawler only sees what makes it into public news coverage. Most
  police-misconduct payouts are small, undisclosed, or simply never
  reported — independent reporting (e.g. The Washington Post's 2022
  investigation) puts the true national total in the **billions** over a
  decade, far above what any news-based crawler will ever surface. The
  "all-time" counter on the site is labeled as a tracked total for exactly
  this reason — it isn't and shouldn't be presented as a complete national
  figure.
- Google News RSS is free and keyless, which also means it's informal —
  Google could change its format at any time. If the crawler starts coming
  back empty, that's the first place to check.
- This tool surfaces candidates; it doesn't replace reading the source.

## License

Do whatever you want with this. No attribution required.
