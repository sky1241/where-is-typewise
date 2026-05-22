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

**Option B — run the radar in CI on a schedule:**

GitHub Actions cron → `python -m src.radar.runner` → push the updated DB back. More moving parts; only set up if you actually want live data on the public dashboard. For the application, Option A is the right call.

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
| Slow first load after long idle | Streamlit Community Cloud cold start | Documented behavior. Send the Loom link instead of the live URL if you need a fast first impression. |

## Cost

Free tier. The dashboard reads SQLite, no per-request inference. The only cost is on Anthropic for the scorer (~$0.50 per 300-thread cycle at Haiku 4.5 prices).
