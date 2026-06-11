# Deploy guide — Streamlit Community Cloud

> Step-by-step. ~5 minutes once you have a Streamlit account. Free tier is enough.

## Prerequisites

- GitHub repo public ✅ (this one already is)
- A Streamlit Community Cloud account at https://share.streamlit.io (sign in with GitHub)
- (Optional) An `ANTHROPIC_API_KEY` if you want the scorer to run live in the cloud — otherwise the dashboard runs on the seed data alone

## Step 1 — Authorize Streamlit on GitHub

1. Go to https://share.streamlit.io
2. "Sign in with GitHub" → authorize for `sky1241`
3. Confirm `sky1241/where-is-typewise` is reachable from the New App picker

## Step 2 — New app

1. Click **New app**
2. **Repository**: `sky1241/where-is-typewise`
3. **Branch**: `main`
4. **Main file path**: `streamlit_app.py` (NOT `src/app.py` — see [BUGS.md](../BUGS.md) BUG-001)
5. **App URL**: pick a slug like `where-is-typewise` → final URL becomes `https://where-is-typewise.streamlit.app`

## Step 3 — Secrets (optional, for live scoring)

In the app's **Settings → Secrets**, paste TOML:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."

# Optional — for live Reddit scraping
REDDIT_CLIENT_ID     = "..."
REDDIT_SECRET        = "..."
REDDIT_USER_AGENT    = "where-is-typewise/0.1 by /u/yourusername"
```

Without these the dashboard still works — it loads the 8-thread demo seed plus whatever live HN + DACH the runner has persisted.

## Step 4 — First boot

1. Click **Deploy!**
2. First build: 90-180 seconds (Streamlit installs requirements.txt)
3. Watch the deploy log for errors. If you see `ModuleNotFoundError: No module named 'src'`, you set the wrong main file — go back to step 2 and confirm it's `streamlit_app.py` at the root.

## Step 5 — Seed the demo data once

The seed runs locally then commits the DB. Two options:

**Option A — pre-commit the demo DB (simpler, recommended for the candidate artifact):**

```bash
python -m src.seed_demo
git add -f data/radar.db
git commit -m "demo: seed initial dashboard data"
git push
```

Streamlit Cloud will rebuild and the dashboard will load with the seed visible. Remove the force-add later when the real runner ships data.

**Option B — run the radar in CI on demand:**

GitHub Actions `workflow_dispatch` → `python -m src.radar.runner` → push the updated DB to a separate `data/latest` branch. Already wired in `.github/workflows/radar.yml` — see [On-demand refresh](#on-demand-refresh-github-actions) below for the setup steps. For the application packet itself, option A is sufficient; option B is for when you want the public dashboard to keep moving past the seed.

## Verifying the deploy

1. Visit the app URL
2. You should see "📡 where-is-typewise" as the H1
3. Headline metric should show "5 threads this week where Typewise should have been mentioned" (matches the seed data)
4. Click any thread expander → see the Claude-drafted reply

If the headline says zero and the table is empty, the demo seed didn't make it into the deployment. Re-check step 5.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'src'` | Wrong main file path | Use `streamlit_app.py`, not `src/app.py` (see BUG-001) |
| "No database found at `data/radar.db`" | DB not in deployment | Either commit `data/radar.db` (option A) or wire CI (option B) |
| Build hangs at "Installing requirements" | `mcp` SDK still resolving | Wait the full 3 minutes, then retry. The MCP SDK itself isn't needed for the dashboard — could be pruned to a `requirements-dashboard.txt` if it keeps biting. |
| Slow first load after long idle | Streamlit Community Cloud cold start | Documented behavior. Expect ~30 s on the first load after a long idle. |

## On-demand refresh (GitHub Actions)

`.github/workflows/radar.yml` re-runs the radar on demand via the **Run
workflow** button. It is deliberately not on a cron: each scoring run spends
real Anthropic API budget (see [Costs](#costs)), so refreshing is an explicit
decision rather than a background expense. Each run does:

1. `python -m src.radar.runner --db data/radar.db --no-reddit -v` (HN + DACH;
   Reddit skipped because CI has no OAuth creds — Anthropic scoring runs iff
   `ANTHROPIC_API_KEY` is set in the repo secrets).
2. A summary print (count by source / locale, scored count, unmentioned-but-
   high-signal count).
3. Force-push of the refreshed `radar.db` to the `data/latest` branch, along
   with a `.source-sha` (which main commit produced it) and `.refreshed-at`
   (ISO timestamp).

`data/latest` is a moving snapshot, not a history — that's why the workflow
force-pushes. main stays free of binary churn.

### Setting up the secret (one-time)

For the workflow's scoring step to actually call Claude (instead of skipping):

1. Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
2. **Name:** `ANTHROPIC_API_KEY`
3. **Secret:** your `sk-ant-...` key
4. Save.

Without this secret, the workflow still runs — the runner skips scoring with a
warning, persists the unscored HN+DACH threads, and publishes the DB. Useful
for keeping the dataset fresh even when you don't want to spend on inference.

(`GITHUB_TOKEN` for the push is provided automatically — no setup needed.)

### Triggering a refresh manually

Repo → **Actions** → **radar-refresh** → **Run workflow** → pick `main` →
**Run**. This is the canonical way to refresh; also useful right after a
config or scorer change to verify nothing surprises you.

### Wiring the refreshed data into the Streamlit dashboard

Streamlit Community Cloud only deploys from main, so it won't pick up
`data/latest` automatically. Three options, easiest first:

1. **Periodic manual merge** (zero infrastructure): when you want the
   dashboard to advance, `git fetch origin data/latest && git checkout
   origin/data/latest -- radar.db && git mv radar.db data/radar.db && git
   commit -m "data: sync latest" && git push`. Streamlit Cloud auto-rebuilds.
2. **Auto-merge PR**: extend the workflow to open a PR on each run with
   `peter-evans/create-pull-request` + auto-merge. Leaves an audit trail in
   PRs but adds noise.
3. **Runtime fetch**: have `src/app.py` download the raw DB from
   `https://raw.githubusercontent.com/<owner>/<repo>/data/latest/radar.db`
   on cold-start. Already supported via the `WIT_DB_PATH` env var pattern —
   point it at a local cache path and fetch on a TTL. More moving parts;
   skip for the candidate artifact.

For the application packet, option 1 once a day is plenty.

## Cost

Free tier. The dashboard reads SQLite, no per-request inference. The only cost is on Anthropic for the scorer (~$0.50 for a cold 300-thread cycle at Haiku 4.5 prices). Already-scored threads are never re-billed — the runner only scores threads with no score in the DB — so a warm refresh costs cents: you pay per *new* thread, not per run. That incremental-cost property is why the workflow is on-demand instead of a cron: each refresh is a deliberate, priced decision.
