---
name: fetch-workday-jobs
description: Fetch job listings and full job descriptions from any Workday-powered careers site (*.myworkdayjobs.com — NVIDIA and much of the Fortune 500) as clean JSON via the unauthenticated `/wday/cxs/` JSON API. Plain curl from Bash — no browser, no credential, no iframe. Use when asked to pull, scrape, enumerate, or monitor jobs on a careers site whose URL contains myworkdayjobs.com, or when a company's careers page turns out to be a Workday React SPA. Covers tenant/site discovery, pagination, facet filters, and job-description HTML stripping; a real-browser fallback exists for tenants that front Cloudflare.
---

# Fetch Workday Jobs via the CXS JSON API

Workday hosts the careers sites of most large companies at
`https://<tenant>.wd<N>.myworkdayjobs.com/<site>`. The visible page is a React
SPA with no server-rendered job content — scraping the DOM is slow and
pagination is click-driven. Skip all of it: every Workday tenant exposes an
**unauthenticated JSON API** under `/wday/cxs/` that serves the listing and the
full job description directly.

> **Verified 2026-07-20 (NVIDIA tenant):** both endpoints return 200 + full
> JSON to plain `curl` — default curl User-Agent, no cookies, no headers beyond
> `Content-Type`. A 73-listing + 12-description sweep completes in ~1 minute
> from Bash.

## ⚠️ Purpose and legal notice

**This skill is for web-service research and educational purposes only.** The
CXS endpoint is each company's own careers-site client API, not a documented
public API; automated access may be restricted by the site's terms of use. Read
only public postings, keep volume low, and pace requests. You are solely
responsible for ensuring your use is lawful and compliant.

## 1. Identify `<tenant>` and `<site>`

Usually straight from the careers URL:

```
https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/...
        └tenant┘└host suffix┘        └────────site────────┘
```

- `tenant` = first subdomain label (`nvidia`); `site` = the path segment after
  the optional `/en-US` locale prefix (`NVIDIAExternalCareerSite`).
- Keep the **full host** including the `wd<N>` number (`wd1`/`wd3`/`wd5`… varies
  per tenant).
- If the URL is ambiguous, load the careers page once in a browser and find any
  XHR to `/wday/cxs/...` in the Network tab — its first two path segments are
  `<tenant>/<site>`.

API base for everything below:

```
BASE = https://<tenant>.wd<N>.myworkdayjobs.com/wday/cxs/<tenant>/<site>
```

## 2. Listings — `POST $BASE/jobs`

```bash
curl -s -X POST "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs" \
  -H "Content-Type: application/json" \
  -d '{"appliedFacets":{},"limit":20,"offset":0,"searchText":"Taipei"}'
```

Response: `{total, jobPostings: [...], facets: [...], userAuthenticated: false}`
where each posting is

```json
{"title": "...", "externalPath": "/job/Taiwan-Taipei/System-Design-Engineer_JR2014482-1",
 "locationsText": "Taiwan, Taipei", "postedOn": "Posted 30+ Days Ago", "bulletFields": ["JR2014482"]}
```

- **`limit` is capped at 20** — larger values return HTTP 400, they are not
  clamped. Paginate with `offset += 20` until you've collected `total`.
- `searchText` is free text (matches titles, locations, keywords). Empty string
  returns everything.
- `bulletFields[0]` is the requisition id (`JR…`) — use it as a stable key.

### Facet filters (precise, beyond `searchText`)

The listing response's `facets[]` enumerates every filter the UI offers, with
tenant-specific GUID values:

```json
{"facetParameter": "jobFamilyGroup",
 "values": [{"descriptor": "Engineering", "id": "0c40f6bd1d8f10ae43ffaefd46dc7e78"}, ...]}
```

Pass the GUIDs back in `appliedFacets`:

```json
{"appliedFacets": {"jobFamilyGroup": ["0c40f6bd1d8f10ae43ffaefd46dc7e78"]},
 "limit": 20, "offset": 0, "searchText": "Taipei"}
```

(Verified: filters NVIDIA 67 Taipei hits → 50 Engineering.) GUIDs differ per
tenant — always read them from an unfiltered response first, never reuse them
across tenants.

## 3. Job detail — `GET $BASE + externalPath`

`externalPath` from the API already starts with `/job/…`, so append it as-is:

```bash
curl -s "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/job/Taiwan-Taipei/System-Design-Engineer_JR2014482-1"
```

Returns `{jobPostingInfo, hiringOrganization, similarJobs, userAuthenticated}`.
`jobPostingInfo` carries `id`, `title`, `jobDescription`, `location`,
`postedOn`, `startDate`, `timeType`, `jobReqId`, `country`, `canApply`,
`externalUrl`, and friends.

**`jobDescription` is raw HTML.** Strip tags before analysis:

```python
text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
```

## 4. Full-sweep recipe (stdlib Python, pastable)

```python
import json, re, time, urllib.request

BASE = "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite"

def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))

def get(path):
    return json.load(urllib.request.urlopen(BASE + path, timeout=30))

jobs, offset = [], 0
while True:
    page = post("/jobs", {"appliedFacets": {}, "limit": 20,
                          "offset": offset, "searchText": "Taipei"})
    jobs += page["jobPostings"]
    offset += 20
    if offset >= page["total"] or not page["jobPostings"]:
        break
    time.sleep(0.5)

for j in jobs:                       # enrich with full JDs
    info = get(j["externalPath"])["jobPostingInfo"]
    j["jobDescription"] = re.sub(r"\s+", " ",
                                 re.sub(r"<[^>]+>", " ", info["jobDescription"]))
    j["jobReqId"] = info["jobReqId"]
    time.sleep(0.5)

print(json.dumps(jobs, ensure_ascii=False, indent=2))
```

Adapt `BASE`, `searchText`, and the enrichment loop (e.g. only enrich a curated
subset). Write output to a file, not the tool return, when sweeping many jobs.

## Cloudflare / WAF fallback

Most tenants (NVIDIA included) accept plain curl. If one returns 403 or a
challenge page:

1. Retry with a real browser User-Agent header first.
2. Still blocked → run the same requests **from inside a real browser tab** on
   that careers site (claude-in-chrome `javascript_tool`, same-origin `fetch()`
   with `credentials: "include"`), exactly like the `fetch-104-jobs` skill's
   happy path — the tab supplies the TLS fingerprint and clearance cookie. Mind
   that skill's ~1000-char return-truncation rule: return short structured
   fields, blob-download anything long.

## Pitfalls

- **`limit` > 20 → HTTP 400** (not clamped). Paginate instead.
- **API `offset` works; the SPA's URL `&offset=N` does not.** If you ever fall
  back to driving the rendered page, pagination is only via clicking the
  `aria-label="page N"` buttons — the URL param is silently ignored. (One more
  reason to stay on the API.)
- **`externalPath` needs no editing when it comes from the API.** Only hrefs
  scraped from the rendered DOM carry a `/en-US/<site>` prefix that must be
  stripped before appending to the CXS base.
- **Same requisition, multiple sites:** postings can appear with `-1`/`-2`
  suffixes on `externalPath` (cross-listings). Dedupe on `jobReqId`
  (`bulletFields[0]`) when counting real openings.
- `userAuthenticated: false` in responses is normal — the API is anonymous.
- Pace requests (~0.5–1 s). The data is a few hundred KB at most; there is no
  reason to hammer the tenant.
