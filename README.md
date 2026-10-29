# Student Resource Finder

A Streamlit app for California college students to discover campus, community,
and public assistance. NVIDIA Nemotron on **Nebius Token Factory** compares
structured answers with retrieved sources and explains next steps. This is
resource discovery, not an eligibility decision.

## Run locally

Python 3.12 recommended. From this project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If secrets.toml already exists, edit it locally instead of replacing it. Never
paste API keys in chat, screenshots, commits, or a public submission.
On macOS/Linux use `.venv/bin/python` in place of the Windows executable.

## Configuration

Add your own Nebius and Tavily keys to `.streamlit/secrets.toml` or environment
variables. The sample contains placeholders only. Model IDs and regions can
change: confirm the configured Nemotron model and endpoint in your Token Factory
project. No OpenAI inference key or local GPU is required.

```toml
NEBIUS_API_KEY = "your-key"
NEBIUS_MODEL = "nvidia/nemotron-3-super-120b-a12b"
NEBIUS_BASE_URL = "https://api.tokenfactory.us-central1.nebius.com/v1"
TAVILY_API_KEY = "your-key"
```

Optional server settings:

- `SRF_GLOBAL_DAILY_LIMIT`: 60 attempted generations per instance per day.
- `SRF_SESSION_HOURLY_LIMIT`: 6 attempted generations per session per hour.
- `SRF_COOLDOWN_SECONDS`: 20 seconds between a session's generations.
- `SRF_USAGE_DB`: durable SQLite path; defaults to `.runtime/usage.sqlite3`.
- `DEMO_ACCESS_CODE`: optional private test access, set in Streamlit secrets.
- `NEBIUS_INPUT_USD_PER_MILLION` and `NEBIUS_OUTPUT_USD_PER_MILLION`: current
  model rates, entered by the operator. Otherwise the exact-model public-catalog
  snapshot in `model_rates.json` is usable for 14 days after its check date;
  another model or a stale snapshot yields an unknown cost. Estimates use
  uncached input pricing and exclude Tavily, discounts, and promotional credits.

The global ceiling survives process restarts when `.runtime` is persistent.
For multiple replicas, use a shared transactional quota service; separate local
SQLite files do not create a cluster-wide ceiling. Ephemeral hosting resets
local files. Provider billing limits remain a second necessary budget control.

## Student flow

1. Start with blank answers or explicitly load **Try an example** (fictional).
2. Select a recognized campus or enter another full name. Campus city/domain
   and home location are separate. The autocomplete is a starter catalog, not
   every California institution.
3. Select needs and answer relevant conditional questions. Age/income can remain
   unknown. No name or first-generation question is collected.
4. Review answers and select **Find Recommendations**.
5. Explore the program cards, filter categories, and save programs in
   this session. **Download saved** exports your shortlist; **Download all**
   exports every recommendation regardless of filters. Both produce printable
   HTML: open the file and choose Print / save as PDF. Saved cards have a green
   border and Saved badge; other cards use the lavender theme.
6. Use **Edit answers** and refresh recommendations to update the plan. A request is
   made only on Generate/Refresh/Update, never on filters, saves, navigation,
   review, or downloads. Recently retrieved sources are reused for 30 minutes.

Editing marks existing results as based on earlier answers until refreshed.
A failed refresh retains the last successful plan. The separate action-plan and
follow-up-question sections are not displayed. Saved programs are limited
to the current recommendations and disappear with the session; no account or
student database is created. Downloads exclude questionnaire answers, though
recommendation explanations can reveal selected needs. Treat downloads privately.

## How source discovery works

- Each selected need gets a separate campus query and/or home-area query.
- Maximum **10 basic Tavily searches**, with up to 3 results each, and **one
  extraction request for up to 12 pages** per uncached generation. This uses
  more search credits than the earlier two-query version. Tavily-reported credits
  are recorded; extraction billing may be rounded/accumulated by the provider.
- Known campus domains constrain school searches. Other recognized campuses'
  pages are rejected. Unknown campus coverage remains explicitly unconfirmed.
- HTTPS `.edu`, `.gov`, `.ca.us` and explicitly approved nonprofit domains are
  accepted. The allowlist is not proof of authenticity, coverage, or eligibility.
- Topic labels use word boundaries in evidence; a query alone does not establish
  that a page serves a topic. Provider and category badges are separate.
- Canonical URLs, normalized titles, and known program aliases remove duplicate
  programs conservatively. This is not perfect entity resolution.
- Page excerpts retain relevant requirement/application paragraphs with a hard
  length cap. Successful page extraction is not a human review or verification.
  Failed extraction stays labeled **Search excerpt only**.
- Retrieval and verification dates are separate. No synthetic verification date
  is assigned to search results. Existing curated review dates belong to records.

## How Nemotron is used

`nebius_ai.py` calls the Token Factory `/v1/chat/completions` inference API with
the configured NVIDIA Nemotron model. It receives selected answers, bounded
evidence, source requirements, and allowable clarification fields. It returns
structured JSON containing up to eight distinct resource IDs, concise plain
language explanations, next actions, relevance levels, and a follow-up field.

The target is 6–8 useful options when supported; fewer are acceptable. The model
orders action priority, including urgent food/housing needs. No program can be
invented by supplying a new ID or URL. Schema and parser checks reject unknown
IDs, duplicate IDs, and incomplete output. Optional summary/follow-up wording
cannot discard a valid plan. Unsafe or overlong card wording is replaced with
bounded source-based guidance, and the interface identifies this recovery. No
automatic paid retry is made. Snippets and known
conflicts cannot receive an unchecked strong label. Mandatory source conflicts
are displayed independently of the model's chosen requirements, with full source
checks retained in printable exports. The source-details/contact-draft popover
is not displayed in the results UI.

These guards do **not** prove generated prose is true. Match labels describe
relevance internally, never approval odds; the UI uses a saved-state badge rather
than match-color badges. Provider review is essential. There is no benefit
amount calculation. General program pages and referrals are labeled accordingly.

## Privacy and reliability

- Selected structured answers go to Nebius only on a generation/update action.
- Campus, broad home city/ZIP, and needs go to Tavily; income, age, insurance,
  dependents, and other personal answers are excluded from search queries.
- No questionnaire answers, request bodies, API keys, or query text are written
  into runtime metrics. SQLite stores random session IDs and request timestamps;
  anonymous JSONL metrics track latency, counts, provider usage, and outcomes.
- API keys stay server-side. No automatic retries or silent paid requests.
- Contact drafts are based on the chosen program/action/checks, contain no
  inserted personal profile, and are never sent automatically.
- Rotate previously disclosed keys in the provider consoles, replace the local
  secret values, restart, then revoke the old keys. Code cannot undo disclosure.

## Verification

```powershell
# Offline: all provider calls mocked
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tests\check_product_flow.py
.\.venv\Scripts\python.exe evaluate.py
# Explicit paid synthetic check: bounded discovery + two model calls
.\.venv\Scripts\python.exe evaluate.py --live
# Anonymous runtime summary
.\.venv\Scripts\python.exe usage_report.py
```

Evaluation covers different campuses, meal plans, enrollment/degree cases,
housing situations, student parents, unknown answers, and out-of-state users.
The offline report verifies candidate rules and structural behavior; it is not
a measurement of real model accuracy. Live output reports retrieved evidence,
rejected campuses, duplicates, latency, tokens, and output changes after one
synthetic insurance clarification. Manually check unsupported claims and actual
usefulness; neither a schema nor token counts establish recommendation quality.

## Deployment and judging

Frontend hosting can be separate from Nebius inference. Configure secrets in the
host's private secret store, install requirements, run `streamlit run app.py`,
use HTTPS, and keep a persistent quota store. Never publish `.runtime`, local
secrets, backups, or synthetic diagnostic artifacts. Test from a separate network.

Target track: Best Apps and Agents. MIT license included. Document actual Nemotron
and Tavily usage accurately. A working public/test URL and submission materials
remain separate release tasks; this repository alone does not establish that a
deployed instance is reachable. Demo video work has intentionally been deferred.

## References

- [Hackathon rules](https://nebiusglobalaihackathon.devpost.com/rules)
- [Tavily Search](https://docs.tavily.com/documentation/api-reference/endpoint/search)
- [Tavily Extract](https://docs.tavily.com/documentation/api-reference/endpoint/extract)
- [UC campus directory](https://www.universityofcalifornia.edu/about-uc/campuses-locations)
- [CSU campus directory](https://www.calstate.edu/attend/campuses)
