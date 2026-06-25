---
name: fetch-104-jobs
description: Fetch structured job and company data from 104 人力銀行 (104.com.tw) through a real browser session. Use when asked to pull, scrape, or enumerate 104 job listings, job details, or a company's openings as clean JSON, when direct HTTP requests are blocked by Cloudflare, or when a previous fetch returned 403. Drives an already-open Chrome tab via the claude-in-chrome MCP tools.
---

# Fetch 104 Job Data via Browser

104.com.tw sits behind Cloudflare **and** a second anti-bot layer. A real
browser session is the reliable way in, but you cannot just `fetch()` the JSON
API — you must let the site's own app make the request and capture it.

## ⚠️ Purpose and legal notice

**This skill is for web-service research and educational purposes only** —
understanding how a modern site's anti-bot layers and client API behave.

**Accessing 104 this way may violate [104 人力銀行's Terms of
Service](https://www.104.com.tw/category/about/terms).** Automated access and
data collection are commonly restricted by site terms. You are solely
responsible for ensuring your use is lawful and compliant; the author accepts no
liability. If in doubt, don't — use 104's official channels instead.

## Scope and etiquette

- Use your own already-open Chrome session. Do **not** log in or attach a
  personal 104 account — an anonymous session carrying only `cf_clearance` is
  enough and is less attributable.
- Read only public job listings — the same data the page already renders.
- Keep request volume low. This is personal, occasional research, not a bulk
  crawler. Respect 104's Terms of Service and `robots.txt`.
- Never enter credentials, never submit an application, never post anything.

## What works and what does not (verified 2026-06-25)

| Approach | Result |
|---|---|
| Real browser loads 104 pages | ✅ passes Cloudflare (`cf_clearance` is valid) |
| The site's **own** XHR to `/jobs/search/api/jobs` | ✅ 200 + full JSON |
| Manual `fetch()` of the same endpoint (isolated world) | ❌ 403 |
| Manual `fetch()` injected into the page's **main** world | ❌ 403 |
| Rendered DOM cards | ✅ present, scrapeable |

The site's app uses **`XMLHttpRequest` (axios), not `fetch`**. `cf_clearance`
clears Cloudflare but a raw request still fails the second layer (the app
attaches per-session context a hand-rolled request can't reproduce). So:

> **Do not blind-fetch the API.** Hook the app's own XHR and trigger the app to
> call the API, then read the captured response.

## Recipe (Chrome + claude-in-chrome MCP)

All JS runs through the `javascript_tool` MCP tool (isolated world). The hook
must be injected into the **main world** via a `<script>` tag. Cross-world
hand-off goes through the shared `localStorage` and DOM, never a `window` var.

> Using cmux's WKWebView browser instead? The technique is identical but the
> command mechanics differ — see [cmux browser variant](#cmux-browser-variant).

### 1. Navigate to the target

```
https://www.104.com.tw/jobs/search/?keyword=<kw>&jobsource=index_s          # search
https://www.104.com.tw/job/<slug>                                            # one job (slug, NOT numeric jobNo)
https://www.104.com.tw/company/<cust_id>?tab=job                             # a company's jobs
```

After navigating, the page renders results into the DOM. Wait ~1–2 s for the
Vue app to hydrate.

### 2. Install the XHR/fetch capture hook (main world)

Idempotent; records any `/api/` or `/ajax/` response into `localStorage` under
`__cap_<n>` keys. Stores the full body separately so large payloads survive.

```js
await (async () => {
  Object.keys(localStorage).filter(k=>/^__cap/.test(k)).forEach(k=>localStorage.removeItem(k));
  const tag = document.createElement('script');
  tag.textContent =
    "(function(){if(window.__h104)return;window.__h104=true;window.__cN=0;"
  + "function save(p,s,t){var i=window.__cN++;try{"
  + "localStorage.setItem('__cap_'+i,JSON.stringify({p:String(p).split('?')[0].replace(/^(https?:)?\\/\\/[^/]+/,''),s:s,len:t.length}));"
  + "localStorage.setItem('__capb_'+i,t);}catch(e){}}"
  + "var of=window.fetch;window.fetch=function(){var a=arguments;return of.apply(this,a).then(function(r){try{var u=(typeof a[0]==='string'?a[0]:(a[0]&&a[0].url))||'';if(/\\/api\\/|\\/ajax\\//.test(u)&&r.ok){r.clone().text().then(function(t){save(u,r.status,t);});}}catch(e){}return r;});};"
  + "var oo=XMLHttpRequest.prototype.open;XMLHttpRequest.prototype.open=function(m,u){this.__u=u;return oo.apply(this,arguments);};"
  + "var os=XMLHttpRequest.prototype.send;XMLHttpRequest.prototype.send=function(){var x=this;x.addEventListener('load',function(){try{var u=x.__u||'';if(/\\/api\\/|\\/ajax\\//.test(u)&&x.status>=200&&x.status<300){save(u,x.status,x.responseText||'');}}catch(e){}});return os.apply(this,arguments);};"
  + "})();";
  document.documentElement.appendChild(tag);
  return 'hook-installed';
})()
```

### 3. Trigger the app to call the API — **in place**

The hook is installed *after* page load, so it misses the initial request.
Make the app fire a fresh request **without navigating**:

- **Search page:** click a **sort** control (`本日最新` / `薪資待遇` / `相關性`)
  or toggle a filter. This re-calls `/jobs/search/api/jobs` via XHR → 200.
- ⚠️ **Pagination (`下一頁`, page numbers) is a FULL PAGE RELOAD** — it wipes the
  hook and the request fires before you can re-attach. To page through, navigate
  to `?...&page=N` then trigger a sort again, or read the DOM (step 6).

```js
await (async () => {
  const el = Array.from(document.querySelectorAll('a,button,li'))
    .find(e => ['薪資待遇','本日最新','相關性'].includes((e.innerText||'').trim()));
  if (!el) return 'no-sort-control';
  el.click();
  await new Promise(r=>setTimeout(r,3000));
  const keys = Object.keys(localStorage).filter(k=>k.startsWith('__cap_'));
  return JSON.stringify(keys.map(k=>JSON.parse(localStorage.getItem(k))));  // [{p,s,len}] — safe scalars
})()
```

You are looking for a capture whose `p` **ends with** `/jobs/search/api/jobs`
with a large `len` (≈130 KB for a page of ~20 results). Always match with
`.endsWith(...)`, never `===`: depending on how 104's axios builds the URL the
captured path can be **protocol-relative** (`//www.104.com.tw/jobs/search/api/jobs`)
rather than a bare `/jobs/...`. The corresponding body is in `__capb_<n>`.

### 4. Export the captured JSON (blob-download)

The MCP layer **blocks** large JSON return values ("Cookie/query string data"
filter) and truncates anything over ~30 KB. The `/jobs/search/api/jobs` body is
~133 KB, so **never return it directly** — download it to disk and read with Bash.

```js
await (async () => {
  const i = Object.keys(localStorage).filter(k=>k.startsWith('__cap_'))
    .map(k=>[k.split('_').pop(), JSON.parse(localStorage.getItem(k))])
    .find(([n,v]) => String(v.p).endsWith('/jobs/search/api/jobs'))?.[0];
  if (i == null) return 'no-jobs-capture';
  const body = localStorage.getItem('__capb_'+i);
  const blob = new Blob([body], {type:'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = '104_jobs_' + Date.now() + '.json';   // unique name; Date.now allowed in page JS
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  return 'download_initiated';
})()
```

Then read it from `~/Downloads/` with Bash (`ls -lt ~/Downloads | head`). The
first download from a new origin prompts the user once; afterward it is silent
for ~5 minutes. Once parsed and processed, see [Cleanup](#cleanup).

### 5. Parse

`/jobs/search/api/jobs` returns `{data:[...], metadata:{pagination:{total,
currentPage, lastPage}}}`. Each `data[]` item includes (verified):
`appearDate, applyCnt, coIndustry, coIndustryDesc, custName, custNo,
description, jobName, salary…` and a `link` object with the job/company URLs.
`custNo` here is the **numeric** company id.

### 6. DOM fallback

When interception is awkward (job-detail and pagination both load on navigation),
read the rendered DOM instead — it always reflects what passed Cloudflare:

- Job-search results cards: `.container-fluid.job-list-container` (around 20 per
  page, but it varies — e.g. 22 — because of inserted promo/info cards and API
  behavior; trust `metadata.pagination.total`, not the per-page count)
- Company-page job cards: `.job-list-container--cprofile`
- Job links: `a[href*="/job/"]` → the slug is the path after `/job/`
- Job detail body: pick the **largest** `.job-description` by `textContent.length`
  (there are 3; the small ones are meta/footer)

## cmux browser variant

Field-verified through cmux's WKWebView browser. The interception technique is
identical; only the wrapper mechanics differ. Each surface command targets a
surface ref (e.g. `surface:7`) returned by `open`.

**Mechanics that differ from the MCP recipe:**

- **`eval` has no top-level `await`.** Write every snippet as a plain
  synchronous IIFE — `(function(){ ... })()` — not `await (async()=>{...})()`.
  For timing, use a separate `cmux browser <surface> wait --function ...`
  command (or a shell `sleep`) instead of an in-page `await new Promise(...)`.
- **Single-quote URLs in the shell.** zsh interprets `?` and `&`, so wrap them:
  `'https://www.104.com.tw/jobs/search/?keyword=python&jobsource=index_s'`.
- **Match the captured path with `.endsWith('/jobs/search/api/jobs')`**, never
  `===` — it can come back protocol-relative (`//www.104.com.tw/...`).
- **`download wait` may report a timeout even though the file landed.** Don't
  trust its result; verify on disk with `find`.

### Flow

```bash
# 1. open (quoted URL); note the returned surface ref
cmux --json browser open 'https://www.104.com.tw/jobs/search/?keyword=python&jobsource=index_s'
#   -> surface:7   (substitute your actual ref below)
cmux browser surface:7 wait --load-state complete --timeout-ms 15000

# 2. install the XHR/fetch hook (synchronous IIFE, no await)
cmux browser surface:7 eval '(function(){if(window.__h104)return;window.__h104=true;window.__cN=0;function save(p,s,t){var i=window.__cN++;try{localStorage.setItem("__cap_"+i,JSON.stringify({p:String(p).split("?")[0].replace(/^(https?:)?\/\/[^/]+/,""),s:s,len:t.length}));localStorage.setItem("__capb_"+i,t);}catch(e){}}var of=window.fetch;window.fetch=function(){var a=arguments;return of.apply(this,a).then(function(r){try{var u=(typeof a[0]==="string"?a[0]:(a[0]&&a[0].url))||"";if((/\/api\/|\/ajax\//).test(u)&&r.ok){r.clone().text().then(function(t){save(u,r.status,t);});}}catch(e){}return r;});};var oo=XMLHttpRequest.prototype.open;XMLHttpRequest.prototype.open=function(m,u){this.__u=u;return oo.apply(this,arguments);};var os=XMLHttpRequest.prototype.send;XMLHttpRequest.prototype.send=function(){var x=this;x.addEventListener("load",function(){try{var u=x.__u||"";if((/\/api\/|\/ajax\//).test(u)&&x.status>=200&&x.status<300){save(u,x.status,x.responseText||"");}}catch(e){}});return os.apply(this,arguments);};})()'

# 3. trigger an in-place sort so the app re-calls the API through the hook
cmux browser surface:7 eval '(function(){var e=Array.prototype.find.call(document.querySelectorAll("a,button,li"),function(x){return ["薪資待遇","本日最新","相關性"].indexOf((x.innerText||"").trim())>=0;});if(e){e.click();return "clicked";}return "no-sort";})()'

# 4. wait until a jobs capture lands (replaces the in-page sleep)
cmux browser surface:7 wait --function 'Object.keys(localStorage).some(function(k){return k.indexOf("__cap_")===0 && String(JSON.parse(localStorage.getItem(k)).p).endsWith("/jobs/search/api/jobs");})' --timeout-ms 12000

# 5. inspect metadata (safe scalars only)
cmux browser surface:7 eval '(function(){var ks=Object.keys(localStorage).filter(function(k){return k.indexOf("__cap_")===0;});return JSON.stringify(ks.map(function(k){var v=JSON.parse(localStorage.getItem(k));return {p:v.p,s:v.s,len:v.len};}));})()'

# 6. blob-download the jobs payload (matches with endsWith)
cmux browser surface:7 eval '(function(){var ks=Object.keys(localStorage).filter(function(k){return k.indexOf("__cap_")===0;});var i=null;ks.forEach(function(k){var v=JSON.parse(localStorage.getItem(k));if(String(v.p).endsWith("/jobs/search/api/jobs"))i=k.split("_").pop();});if(i===null)return "no-jobs-capture";var body=localStorage.getItem("__capb_"+i);var b=new Blob([body],{type:"application/json"});var a=document.createElement("a");a.href=URL.createObjectURL(b);a.download="104_jobs_"+Date.now()+".json";document.body.appendChild(a);a.click();document.body.removeChild(a);return "download_initiated";})()'

# 7. VERIFY ON DISK — download wait often times out even on success, so don't rely on it
cmux browser surface:7 download wait --timeout-ms 8000 || true
find ~/Downloads -name '104_jobs_*.json' -mmin -5
```

Read the newest match from `~/Downloads/` with Bash. (The body is ~130 KB; if
cmux returns large `eval` strings cleanly on your build you can also pull it via
`cmux browser surface:7 storage local get __capb_<i>` and skip the download.)
Once parsed and processed, see [Cleanup](#cleanup).

**Tip:** `cmux browser <surface> addinitscript --script '<hook>'` installs the
hook *before* the page's own scripts run, so a fresh `open`/`reload` captures
the **initial** API call with no sort-trigger needed. Promising for cmux but not
yet field-verified for 104; the sort-trigger flow above is what's confirmed.

## Cleanup

The downloaded dump in `~/Downloads/` (e.g. `104_jobs_1750000000000.json`) is
scratch data — it is not the deliverable, just the transport for the captured
JSON. **After you have read and processed it, remind the user that the file is
still sitting in `~/Downloads/` and ask whether to delete it.** Never remove it
unprompted: it lives in the user's personal Downloads folder, and a wildcard
could catch unrelated files.

```bash
# only after the user confirms — prefer the exact filename you created:
rm "$HOME/Downloads/104_jobs_<timestamp>.json"
```

## Endpoint reference

Verified reachable **as the app's own XHR** (capture, don't blind-fetch):

| Endpoint | Returns |
|---|---|
| `/jobs/search/api/jobs?keyword=&order=&page=&pagesize=20` | search results (`data[]` + pagination) |
| `/jobs/search/ajax/cards` | UI flags (student/résumé cards) — not job data |
| `/job/ajax/content/<slug>` | one job's full detail (`data.header/jobDetail/condition…`, `data.custNo` = short-code company id) |
| `/api/companies/<cust_id>/jobs?page=1&pageSize=20` | a company's openings, paginated |
| `/api/companies/<cust_id>/content` · `/news` · `/api/companies/ratings?custNos=` | company profile / news / ratings |

`order`: `15` relevance · `16` newest · `13` salary. `cust_id` has two forms —
short code (`1a2x6bmxfl`, used in `/company/` URLs and `/api/companies/`) vs
numeric `custNo` (`130000000230849`). The job-detail API's `data.custNo` is the
short code.

Static reference tables need no browser (plain `fetch`/curl, no Cloudflare):
`https://static.104.com.tw/category-tool/json/Area.json` (areas) and
`.../JobCat.json` (job categories).

## Pitfalls

- **403 on any hand-rolled request** — including from the main world. Always go
  through the app's own XHR. There is no header set that makes a raw fetch pass.
- **fetch vs XHR** — 104 uses axios/XHR; a `fetch`-only hook captures nothing.
- **Protocol-relative paths** — 104's axios issues `//host/path` URLs. Normalize
  with `^(https?:)?\/\/[^/]+` and match captured paths with `.endsWith()`, never
  `===`, or you will miss the capture.
- **Isolated vs main world** — `javascript_tool` runs isolated; the hook needs a
  `<script>` injection to run in the main world. Bridge via `localStorage`/DOM.
- **Pagination reloads** — only sort/filter are in-place; pagination navigates.
- **Big returns get blocked/truncated** — blob-download anything over ~30 KB.
- **JS context dies on navigation** — re-install the hook after every navigation.
