# Battle Plan v2 — extend MCP to a 7-tool Growth Playbook

**Why this exists:** the first 4-hour pass shipped MCP with 4 tools (compare, pricing, case_study, integration_check), focused on *buyer evaluation*. The Typewise job posting demands a "documented, automated Growth Playbook" and lists **Reddit, podcasts, YouTube, influencers, industry associations, communities** as channels to attack. The first pass covered Reddit + HN + DACH RSS. This pass extends the MCP — not the radar — to give the Typewise team three more growth surfaces a dev can fire from Claude Desktop.

**Time budget:** 1h45 strict. Sky has ~2 h left of the 4 h artifact window.

**Cousin pc1 runs Option 3 in parallel** (GitHub Actions scheduled radar). No file conflicts — they touch `.github/workflows/` and a new secret, I touch `src/mcp_server/`.

---

## Deep audit — wiring pattern to copy exactly

Every existing tool follows the same five-file shape. Any new tool that breaks this shape is wrong.

| Layer | File | Pattern |
|---|---|---|
| Data | `src/mcp_server/data/<name>.json` | Curated static dict + `_meta` block with `last_updated` and `source` and a `warning` field that flags any assumption |
| Logic | `src/mcp_server/tools/<name>.py` | Pure functions: `_load()`, alias map, scoring helpers, public `compare/find/check/...` returning a `dict` |
| Surface | `src/mcp_server/server.py` | `from src.mcp_server.tools import <name> as <name>_mod` + `@mcp.tool()` def that delegates to `<name>_mod.<func>()` |
| Unit | `tests/test_<name>.py` | 6–10 tests: happy path, alias resolution, unknown input fallback, edge cases, evidence shape |
| Protocol | `tests/test_mcp_integration.py` | Add a `test_<name>_tool_callable_via_mcp_returns_<x>` async test |

**Verbatim header for every new `<name>.json`:**

```json
{
  "_meta": {
    "last_updated": "2026-05-22",
    "source": "curated from public material",
    "warning": "<assumption flag>"
  },
  ...
}
```

---

## Chunks

### Chunk 1 — `typewise_podcast_pitch(podcast_name)` (30 min)

**What it solves from the job posting:** *"podcasts, ... or channels nobody has thought of yet."* Lets a Typewise team member instantly draft a guest-pitch for any of the ten podcasts where David or Janis should appear, with the host's known angle and a recent-episode link.

**Files:**
- `src/mcp_server/data/podcasts.json` — 10 podcasts: No Priors, The CX Cast (Forrester), Modern Customer (Blake Morgan), Be Customer Led (Bill Staikos), Punk CX (Adrian Swinscoe), Support Driven Podcast, 20VC, SaaStr, Lenny's Podcast, Acquired. Each entry: `name`, `host`, `focus`, `audience_size`, `host_angle`, `recent_episode_url`, `contact_hint`, `recommended_typewise_angle`.
- `src/mcp_server/tools/podcast_pitch.py` — `pitch(podcast_name) -> dict` with `podcast`, `recommended_pitch` (3-paragraph draft), `talking_points` (4-bullet list), `next_step`, `evidence` (recent_episode_url).
- `tests/test_podcast_pitch.py` — 6 tests: known podcast returns full structure, alias resolves (e.g. "CX Cast" → "The CX Cast"), unknown returns the curated list, pitch text references the host's angle, no-empty-fields invariant, case-insensitive lookup.

**Acceptance:** `python3 -c "from src.mcp_server.tools.podcast_pitch import pitch; import json; print(json.dumps(pitch('No Priors'), indent=2))"` returns a structured dict where `recommended_pitch` is 200–400 chars and references Sarah Guo or Elad Gil.

**Forge:** run after pytest passes locally — must show no regression vs prior 125-test baseline.

---

### Chunk 2 — `typewise_linkedin_post(topic)` (30 min)

**What it solves:** *"Build AI-powered systems that let you operate at the scale of a full marketing team alone."* The job audit identified founder LinkedIn cadence (Jesse Zhang's playbook) as a free real-estate channel Typewise isn't using. This tool turns a topic into a posting template tuned for David or Janis.

**Files:**
- `src/mcp_server/data/linkedin_templates.json` — 6 topics: `augment_vs_replace`, `eu_data_residency`, `dach_case_study`, `agent_vs_chatbot`, `multi_agent_orchestration`, `helpdesk_layer_not_replacement`. Each: `topic`, `hook`, `insight`, `cta`, `hashtags`, `target_audience`, `tone_notes`, `inspired_by` (a real LinkedIn pattern reference).
- `src/mcp_server/tools/linkedin_post.py` — `generate(topic) -> dict` with `topic`, `draft_post` (assembled hook + insight + cta), `hashtags`, `tone_notes`, `length_chars`, `target_persona`.
- `tests/test_linkedin_post.py` — 6 tests: known topic returns full structure, draft_post length is in 600–1500 chars (LinkedIn sweet spot), hashtags are ≥3, alias map ("eu data" → "eu_data_residency"), unknown topic returns curated list, no-empty-fields invariant.

**Acceptance:** `generate("eu_data_residency")` returns `draft_post` of 600–1500 chars containing "ISO 27001" or "EU".

**Forge:** must pass after this chunk.

---

### Chunk 3 — `typewise_influencer_finder(topic)` (30 min)

**What it solves:** *"influencers"* from the job verbatim. Maps a topic to the right CX influencer to engage (LinkedIn comment, podcast guest pitch, sponsored newsletter slot).

**Files:**
- `src/mcp_server/data/influencers.json` — 12 CX influencers: Shep Hyken, Jeanne Bliss, Blake Morgan, Bill Staikos, Adrian Swinscoe, Dan Gingiss, Annette Franz, Stacy Sherman, Justin Robbins, Nate Brown, Jeannie Walters, Sarah Guo. Each: `name`, `role`, `audience_size`, `channels` (linkedin/twitter/podcast/newsletter), `topics_focus` (3–5 tags), `best_outreach_channel`, `notes`.
- `src/mcp_server/tools/influencer_finder.py` — `find(topic) -> dict` with `query`, `best_matches` (up to 3 ranked influencers), `reasoning`. Topic matched via case-insensitive tag overlap scoring.
- `tests/test_influencer_finder.py` — 7 tests: known topic returns ≥1 match, unknown topic returns ≥1 fallback, alias map ("cx automation" → "automation"), best match has highest topic-overlap count, no-influencer-listed-twice invariant, channels field is always a list, audience_size is always int.

**Acceptance:** `find("ai automation")` returns 1–3 ranked influencers, each with `reasoning` referencing the overlapping tag.

**Forge:** must pass.

---

### Chunk 4 — Wire + integration tests + README + push (15 min)

**Files touched:**
- `src/mcp_server/server.py` — add 3 imports + 3 `@mcp.tool()` defs. Total tools: 4 → 7.
- `tests/test_mcp_integration.py` — rename `test_server_exposes_four_tools` → `test_server_exposes_seven_tools`. Add 3 async `test_<name>_tool_callable_via_mcp_returns_<x>`.
- `README.md` — update the "four tools" list to seven, with one-line each.
- `docs/APPLICATION.md` — bump the MCP brag from 4 → 7 tools in the candidacy email draft.

**Final QA:**
1. `python3 -m pytest tests/ -v` → must show **~150 tests passing** (125 + ~18 new across chunks 1–3 + 3 integration).
2. `forge` → PASS, no regression.
3. `git add -A && git commit && git push`.

---

## Why this matters more than extending the radar

Extending the radar to YouTube adds **one channel** but at high risk (transcript anti-bot, slow scoring). Extending the MCP to 7 tools turns the *Typewise team itself* into a faster operator: anyone with Claude Desktop can now ask "draft me a podcast pitch for No Priors", "give me a LinkedIn post on EU data residency", "who should I reach out to about AI automation in CS?" — and get an actionable structured answer in two seconds.

That is the *"documented, automated Growth Playbook"* outcome the job posting names. Not in a deck. In code.

---

## Failure mode if time runs out

Ship chunks in order. If only chunk 1 lands, the MCP still has +1 tool (podcasts). If chunks 1+2 land but not 3, the MCP has +2. Each chunk is independently committable and useful.

**Hard rule:** no chunk gets committed until both its unit tests and forge pass clean.
