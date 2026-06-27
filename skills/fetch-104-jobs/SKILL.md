---
name: fetch-104-jobs
description: Fetch structured job and company data from 104 人力銀行 (104.com.tw) through a real browser session. Use when asked to pull, scrape, or enumerate 104 job listings, job details, or a company's openings as clean JSON. The reliable path is a same-origin `fetch()` of 104's JSON API from inside an already-open Chrome tab (claude-in-chrome MCP) — the browser supplies the Cloudflare clearance and TLS fingerprint. Use this skill when direct HTTP/curl requests are blocked by Cloudflare or returned 403.
---

# Fetch 104 Job Data via Browser

104.com.tw sits behind Cloudflare. The reliable way in is a **real browser
session**: load any 104 page (which passes the Cloudflare challenge and sets the
`cf_clearance` cookie), then make a **same-origin `fetch()`** of 104's JSON API
*from that tab*. The request rides the genuine browser session — real TLS
fingerprint, real cookies — so it returns clean JSON with no scraping.

This is the same insight as the `curl_cffi impersonate="chrome"` trick that
out-of-browser tools use to forge a Chrome TLS fingerprint — except a real
Chrome **is** a real Chrome, so you skip the impersonation entirely and let the
browser you already control issue the request.

> **Verified 2026-06-26:** a same-origin `fetch()` with `credentials:"include"`
> returns **200 + full JSON** for the search, job-detail, and company endpoints —
> no XHR hook, no sort-trigger, no blob-download.
>
> ⚠️ A 2026-06-25 test of the *same* fetch returned **403**, which is why the
> XHR-capture technique below exists. 104's anti-bot behavior is **inconsistent**
> across days/sessions. **Try the direct fetch first; if it 403s, fall back to
> [XHR capture](#fallback-a-direct-fetch-returns-403).**

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
- Keep request volume low and pace yourself (≥1 s between calls). This is
  personal, occasional research, not a bulk crawler. Respect 104's Terms of
  Service and `robots.txt`.
- Never enter credentials, never submit an application, never post anything.

## The approach in three steps

1. **Navigate** a Chrome tab to a 104 page (passes Cloudflare → sets
   `cf_clearance`, and makes subsequent calls same-origin).
2. **`fetch()`** the JSON API from that tab with `credentials:"include"`.
3. **Parse in-page and return a structured projection** — an array of objects
   with short fields, never one giant JSON string (see
   [the truncation rule](#3-return-structured-data-never-one-big-string)).

All JS runs through the `javascript_tool` MCP tool (isolated world). That world
**can** issue a successful same-origin `fetch()` because cookies are per-origin,
not per-world — no main-world `<script>` injection or `localStorage` bridge is
needed for the happy path.

> Using cmux's WKWebView browser instead? The technique is identical; only the
> command mechanics differ — see [cmux browser variant](#cmux-browser-variant).

## Recipe (Chrome + claude-in-chrome MCP)

### 1. Navigate to a 104 page

Any `www.104.com.tw` page works (it just needs to clear Cloudflare and be
same-origin with the API). The natural choice is the search page itself:

```
https://www.104.com.tw/jobs/search/?keyword=<kw>&jobsource=index_s          # search
https://www.104.com.tw/job/<slug>                                            # one job (slug, NOT numeric jobNo)
https://www.104.com.tw/company/<short_code>?tab=job                          # a company's jobs
```

Wait ~1–2 s after navigating. (You don't need the DOM to hydrate for the fetch
to work — you only need the page loaded so `cf_clearance` is set — but a brief
wait avoids racing the initial challenge.)

### 2. Fetch the JSON API directly

A reusable helper. The three headers mirror what 104's own app sends; the
`Referer` should point at a matching 104 page.

```js
await (async () => {
  async function api(url, ref) {
    const r = await fetch(url, {
      headers: {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-TW,zh;q=0.9',
        'Referer': ref || 'https://www.104.com.tw/jobs/search/'
      },
      credentials: 'include'      // attaches cf_clearance; required
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);   // 403 here => use Fallback A
    return r.json();
  }
  const j = await api('https://www.104.com.tw/jobs/search/api/jobs?keyword=SRE&order=16&page=1&pagesize=20&kwop=7');
  // ... project & return (see step 3)
})();
```

### 3. Return STRUCTURED data, never one big string

The MCP/tool layer **truncates each individual string value in a return at
~1000 chars** (verified). A page of ~20 results stringified is ~30–130 KB, so
**never `return JSON.stringify(wholeResponse)`** — it gets cut mid-string.

Instead, **parse in-page and return an array of objects with short fields**.
Many short strings pass fine; only a single >1000-char string gets clipped.

```js
await (async () => {
  const r = await fetch('https://www.104.com.tw/jobs/search/api/jobs?keyword=SRE&order=16&page=1&pagesize=20&kwop=7', {
    headers: { 'Accept':'application/json, text/plain, */*', 'Accept-Language':'zh-TW,zh;q=0.9', 'Referer':'https://www.104.com.tw/jobs/search/' },
    credentials: 'include'
  });
  if (!r.ok) return 'HTTP ' + r.status;          // 403 => Fallback A
  const j = await r.json();
  return {
    total: j.metadata.pagination.total,
    page:  j.metadata.pagination.currentPage,
    last:  j.metadata.pagination.lastPage,
    jobs: j.data.map(d => ({
      name:  d.jobName,
      co:    d.custName,
      area:  d.jobAddrNoDesc,
      sal:   d.salaryDesc,
      appear: d.appearDate,
      applies: d.applyCnt,
      slug:  (String(d.link && d.link.job ).match(/\/job\/([^?]+)/)    || [])[1],  // for job detail
      coShort: (String(d.link && d.link.cust).match(/\/company\/([^?]+)/)|| [])[1]  // short code for company API
    }))
  };
})();
```

**Long single fields** (a full job description from the detail endpoint can
exceed 1000 chars) will still clip. For those: return them split into chunks,
or use [Fallback B (blob-download)](#fallback-b-need-the-full-raw-payload-on-disk),
or read the rendered DOM ([DOM fallback](#dom-fallback)).

### Job detail

```js
await (async () => {
  const slug = '91u53';  // from a search result's link.job
  const r = await fetch('https://www.104.com.tw/job/ajax/content/' + slug, {
    headers: { 'Accept':'application/json, text/plain, */*', 'Referer':'https://www.104.com.tw/job/' + slug },
    credentials: 'include'
  });
  if (!r.ok) return 'HTTP ' + r.status;
  const d = (await r.json()).data;
  return {
    name: d.header && d.header.jobName,
    co:   d.header && d.header.custName,
    coShort: d.custNo,                              // SHORT code here (not numeric)
    salary: d.jobDetail && d.jobDetail.salary,
    descLen: (d.jobDetail && d.jobDetail.jobDescription || '').length,  // long: chunk/disk if you need the text
    needExp: d.condition && d.condition.workExp,
    edu:     d.condition && d.condition.edu
  };
})();
```

### A company's openings

The company-jobs endpoint takes the **short code** (e.g. `dbgeqqo` from a result's
`link.cust` → `/company/dbgeqqo`), **not** the numeric `custNo`. Passing the
numeric id returns `totalCount: 0`.

```js
await (async () => {
  const code = 'dbgeqqo';
  const r = await fetch('https://www.104.com.tw/api/companies/' + code + '/jobs?page=1&pageSize=20', {
    headers: { 'Accept':'application/json, text/plain, */*', 'Referer':'https://www.104.com.tw/company/' + code + '?tab=job' },
    credentials: 'include'
  });
  if (!r.ok) return 'HTTP ' + r.status;
  const data = (await r.json()).data;
  return {
    total: data.totalCount, pages: data.totalPages,
    jobs: (data.list.normalJobs || []).map(j => ({ name: j.jobName, appear: j.appearDate }))
  };
})();
```

## Endpoint and parameter reference

Reachable via same-origin `fetch()` from a loaded 104 tab (`credentials:"include"`):

| Endpoint | Returns |
|---|---|
| `/jobs/search/api/jobs?keyword=&order=&page=&pagesize=20&kwop=7` | search results (`data[]` + `metadata.pagination`) |
| `/job/ajax/content/<slug>` | one job's full detail (`data.header / jobDetail / condition`; `data.custNo` = **short** company code) |
| `/api/companies/<short_code>/jobs?page=1&pageSize=20` | a company's openings, paginated |
| `/api/companies/<short_code>/content` · `/news` | company profile / news |
| `/api/companies/ratings?custNos=<numeric>` | company ratings (numeric `custNo`) |
| `/jobs/search/ajax/cards` | UI flags (student/résumé cards) — not job data |

**Search query parameters** (names + codes from the `job104-mcp` project, cross-checked live):

| Param | Meaning | Values |
|---|---|---|
| `keyword` | search term | free text |
| `kwop` | keyword operator | `7` (match all) |
| `order` | sort | `15` relevance (default) · `16` newest · `13` salary |
| `page` / `pagesize` | pagination | `pagesize` ≈ 20 per page |
| `area` | location code(s) | from `Area.json` (comma-joined) |
| `jobcat` | job-category code(s) | from `JobCat.json` (comma-joined) |
| `scmin` | minimum salary | integer |
| `scstrict` | enforce salary floor | `1` |
| `remoteWork` | remote | `1` full · `2` partial (combine `1,2`) |
| `wt` | employment type | `1` 全職 · `2` 兼職 · `3` 高階 · `4` 派遣 · `5` 接案 |
| `jobexp` | required experience | years (string) |
| `edu` | education level | code (string) |
| `isnew` | recency filter | days (job104-mcp sends `7`) |

`custNo` has two forms: the **short code** (`dbgeqqo`, used in `/company/` URLs,
`/api/companies/`, and the job-detail `data.custNo`) vs the **numeric** id
(`28990860000`, used in search `data[].custNo` and the ratings endpoint). They
are not interchangeable.

### Code tables (no browser needed)

Area and job-category codes are static and **not** behind Cloudflare — fetch them
with a plain `fetch`/curl from anywhere:

```
https://static.104.com.tw/category-tool/json/Area.json      # area codes
https://static.104.com.tw/category-tool/json/JobCat.json    # job-category codes
```

Resolve a Chinese name (e.g. 台北市, 軟體工程師) to its code here, then pass the
code as `area` / `jobcat`. Cache them locally; they change rarely.

## Fallback A: direct fetch returns 403

If step 2 throws `HTTP 403`, 104's second anti-bot layer is active this session.
Don't fight it with headers — **no header set makes a raw fetch pass** when this
layer is on. Instead, let the site's **own** app issue the request and capture
the response. (104's app uses `XMLHttpRequest`/axios, not `fetch`.)

Inject a capture hook into the **main world** (the `javascript_tool` isolated
world can't see the app's XHR), then trigger an in-place re-fetch and read the
captured body from `localStorage`.

```js
// 1. install hook (main world via <script>); idempotent; records /api/ & /ajax/ responses
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

```js
// 2. trigger an IN-PLACE re-fetch by clicking a sort control (re-calls /jobs/search/api/jobs via XHR)
await (async () => {
  const el = Array.from(document.querySelectorAll('a,button,li'))
    .find(e => ['薪資待遇','本日最新','相關性'].includes((e.innerText||'').trim()));
  if (!el) return 'no-sort-control';
  el.click();
  await new Promise(r=>setTimeout(r,3000));
  return JSON.stringify(Object.keys(localStorage).filter(k=>k.startsWith('__cap_'))
    .map(k=>JSON.parse(localStorage.getItem(k))));   // [{p,s,len}] — safe scalars
})()
```

Find the capture whose `p` **ends with** `/jobs/search/api/jobs` (match with
`.endsWith()`, never `===` — 104's axios sometimes issues protocol-relative
`//host/path` URLs). Its body is in `__capb_<n>`. Then parse it in-page and
return a structured projection exactly as in [step 3](#3-return-structured-data-never-one-big-string),
or export it via Fallback B.

> ⚠️ **Pagination (`下一頁`, page numbers) is a FULL PAGE RELOAD** — it wipes the
> hook before you can read the response. To page through under this fallback,
> navigate to `?...&page=N`, re-install the hook, and trigger a sort again.

## Fallback B: need the full raw payload on disk

When you want the **complete raw JSON** (archival, or a payload with long fields
that the ~1000-char return cap would clip), download it to disk and read it with
Bash instead of returning it.

```js
// from a captured body in localStorage (Fallback A) ...
await (async () => {
  const i = Object.keys(localStorage).filter(k=>k.startsWith('__cap_'))
    .map(k=>[k.split('_').pop(), JSON.parse(localStorage.getItem(k))])
    .find(([n,v]) => String(v.p).endsWith('/jobs/search/api/jobs'))?.[0];
  if (i == null) return 'no-jobs-capture';
  const body = localStorage.getItem('__capb_'+i);
  // ... or, on the happy path, just: const body = JSON.stringify(await (await fetch(url,{credentials:'include'})).json());
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([body], {type:'application/json'}));
  a.download = '104_jobs_' + Date.now() + '.json';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  return 'download_initiated';
})()
```

Read it from `~/Downloads/` with Bash (`ls -lt ~/Downloads | head`). The first
download from a new origin prompts the user once; afterward it is silent for
~5 minutes. After processing, see [Cleanup](#cleanup).

## DOM fallback

When the API is unavailable and you only need what's on screen, read the
rendered DOM — it always reflects what passed Cloudflare:

- Search results cards: `.container-fluid.job-list-container` (~20/page, varies —
  promo/info cards inflate the count; trust `metadata.pagination.total`)
- Company-page job cards: `.job-list-container--cprofile`
- Job links: `a[href*="/job/"]` → the slug is the path after `/job/`
- Job-detail body: pick the **largest** `.job-description` by
  `textContent.length` (there are ~3; the small ones are meta/footer)

## cmux browser variant

Field mechanics differ from the MCP recipe; the fetch technique is identical.
Each command targets a surface ref (e.g. `surface:7`) returned by `open`.

- **`eval` has no top-level `await`.** Write a synchronous IIFE that kicks off
  the fetch and stashes the result, then poll with a separate `wait`/`storage`
  command — don't rely on in-page `await`.
- **Single-quote URLs in the shell** — zsh eats `?` and `&`.
- **`wait --function` can spuriously time out** even when the value is already
  set (observed for the detail fetch). The fetch resolves in <1 s, so just read
  the stashed value directly — don't abort the flow on a wait timeout.
- Match captured paths (Fallback A) with `.endsWith('/jobs/search/api/jobs')`.

```bash
# 1. open (quoted URL); note the returned surface ref
cmux --json browser open 'https://www.104.com.tw/jobs/search/?keyword=python&jobsource=index_s'
#   -> surface:7
cmux browser surface:7 wait --load-state complete --timeout-ms 15000

# 2. direct fetch -> stash result in localStorage (synchronous IIFE; no await)
cmux browser surface:7 eval '(function(){fetch("https://www.104.com.tw/jobs/search/api/jobs?keyword=python&order=16&page=1&pagesize=20&kwop=7",{headers:{"Accept":"application/json, text/plain, */*","Referer":"https://www.104.com.tw/jobs/search/"},credentials:"include"}).then(function(r){return r.text();}).then(function(t){localStorage.setItem("__104",t);}).catch(function(e){localStorage.setItem("__104","ERR:"+e);});return "started";})()'

# 3. wait until the result lands
cmux browser surface:7 wait --function 'localStorage.getItem("__104")!==null' --timeout-ms 12000

# 4. pull it (small projection) OR blob-download for the full body
cmux browser surface:7 eval '(function(){var j=JSON.parse(localStorage.getItem("__104"));return JSON.stringify({total:j.metadata.pagination.total,jobs:j.data.map(function(d){return {name:d.jobName,co:d.custName,slug:(String(d.link&&d.link.job).match(/\/job\/([^?]+)/)||[])[1]};})});})()'
```

If the direct fetch 403s under cmux too, use the Fallback A hook (the
`addinitscript` form below catches even the page's *initial* XHR):

```bash
cmux browser surface:7 addinitscript --script '<the main-world hook from Fallback A>'
# then reload; the initial /jobs/search/api/jobs call is captured with no sort-trigger
```

> Note: `download wait` may report a timeout even though the file landed —
> verify on disk with `find ~/Downloads -name '104_jobs_*.json' -mmin -5`.

## Cleanup

Only relevant if you used **Fallback B**. The dump in `~/Downloads/` (e.g.
`104_jobs_1750000000000.json`) is scratch transport, not the deliverable. **After
reading and processing it, tell the user it's still in `~/Downloads/` and ask
whether to delete it.** Never remove it unprompted — it's in the user's personal
Downloads folder and a wildcard could catch unrelated files.

```bash
# only after the user confirms — prefer the exact filename you created:
rm "$HOME/Downloads/104_jobs_<timestamp>.json"
```

## Pitfalls

- **Try direct fetch first.** It's verified working and far simpler than the
  capture dance. Only fall back to XHR capture on an actual 403.
- **`credentials:"include"` is required** — without it `cf_clearance` isn't sent
  and the request fails. And you must already be on a loaded 104 page (same-origin
  + clearance set).
- **Return structured data, not a big string** — each returned string value is
  truncated at ~1000 chars. Project to arrays of short fields; chunk or
  blob-download long fields (job descriptions).
- **Company endpoint wants the short code**, not the numeric `custNo` — numeric
  silently returns `totalCount: 0`.
- **104's anti-bot is inconsistent** — the direct fetch may 200 one day and 403
  the next. Keep Fallback A ready; re-verify before assuming either result.
- **The REPL keeps globals between `javascript_tool` calls** — wrap each snippet
  in an IIFE (`await (async()=>{...})()`) so `const`/`let` don't collide across
  calls.
- **Fallback A only**: 104 uses axios/XHR (a fetch-only hook captures nothing);
  paths can be protocol-relative (match with `.endsWith()`); the hook runs in the
  main world (bridge via `localStorage`); pagination is a full reload that wipes
  the hook; re-install the hook after every navigation.
