# 대가들의 선택 (13F) — handover

> Agent-facing working doc. Written for a fresh session to resume this project
> in a different window. Dense on purpose; the repo owner does not need to read it.
> Prose language here is English for density — **all user-facing output and all
> conversation with the owner is Korean.** Owner is a non-developer: no terminal,
> no git. See `/CLAUDE.md` §0.

STATUS as of 2026-09-14: **probe ran once, successfully. SEC is reachable from a runner.**
`SEC_CONTACT` is set; run #1 (2026-09-14, 12s) came back **200 on every request**.
What it found is in §5-2 — read that before anything else. Nothing is parsed yet,
no schema exists, no page exists. Everything below §4 is decided, not speculative.

---

## 1. What this is

Separate product from the `itpaidoff.com` dashboard. Owner considers **this** the
main product; the market-timing dashboard is a side branch that is now essentially
finished.

Show what famous investors bought **and what that choice turned into.**

**The differentiator is outcome, not position.** A Korean app already lists current
holdings (not the owner's). Do not rebuild that. The question this answers is
"그래서 어떻게 됐나" — how did it work out. Domain name `itpaidoff.com` was chosen
for exactly this meaning, before the product.

---

## 2. Why 13F

SEC Form 13F. **US government work → public domain.** This removes the entire
data-licensing problem documented in `/CLAUDE.md` §11 that constrains the
dashboard. Biggest single advantage of this project.

Filers: US institutional managers with >$100M in §13(f) securities.
Cadence: quarterly, **due 45 days after quarter end.**

**Shows:** US-listed long equity, ETFs, ADRs, some options/convertibles.
**Does not show:** shorts, cash, bonds, futures, currencies, commodities,
swaps, foreign-listed, private. Both limits must be stated on screen.

---

## 3. Investor selection — the four tests

**Do not rank by fame.** 13F representativeness varies enormously by manager, and
a fund whose 13F is unrepresentative will actively mislead readers. Screen every
candidate through all four:

```
T1  Does 13F cover MOST of their risk?        macro / multi-strat / market-maker → fail
T2  Do they still personally run it?           → fail on handover
T3  Few enough positions to be a story?        quant with 1,000+ names → fail
T4  Do they already disclose better themselves? → fail if yes
```

### Accepted — first eight (owner approved the direction, list is mine)

```
Buffett / Berkshire Hathaway      ~40 pos, 13F ≈ whole portfolio   ← START HERE
Ackman / Pershing Square          ~8-10 pos, extremely concentrated
Chris Hohn / TCI                  ~10-12 pos
Li Lu / Himalaya Capital          very few pos
Mohnish Pabrai / Dalal Street     very few pos
Terry Smith / Fundsmith           ~30 pos, long holding periods
David Tepper / Appaloosa          concentrated
Michael Burry / Scion             EXCEPTION — see below
```

**Burry is a deliberate exception.** He turns positions over fast, so the 45-day
delay hurts him most (fails the spirit of T3). Kept for search demand (The Big
Short). His page must carry a **louder** staleness warning than the others.

### Rejected — and why (record so nobody re-proposes)

```
Ray Dalio / Bridgewater   FAILS T1 + T2.
                          T1: 13F is mostly ETFs; the macro bets live in futures,
                              FX and bonds, none of which 13F shows. Holdings shown
                              are REAL but a minority of risk → reader concludes
                              "Dalio buys EM ETFs", which is false. A footnote does
                              not fix this; the screen would still show an ETF list.
                          T2: handed over control of Bridgewater in Oct 2022. Current
                              filings are not his picks at all.
                          Owner asked about Dalio directly on 2026-09-14 and accepted
                          this answer. Do not re-propose.

Renaissance Technologies  FAILS T3 (thousands of positions), and T1 in spirit —
                          45-day-old quant positions are already closed.
Citadel / Millennium      FAILS T1 (huge invisible short book) and T3.
Cathie Wood / ARK         FAILS T4 — ARK publishes daily holdings itself.
                          Our quarterly view is strictly worse than her free data.
```

---

## 4. DECIDED: build Berkshire only, first

Owner: "그럼, 우선 한명만 해야지" (2026-09-14).

**Berkshire is first for a reason beyond passing all four tests: it is the only
one we can verify against.** Berkshire publishes holdings and cost basis in its
annual report. Reconcile our 13F-derived numbers against that to prove the
pipeline is right. No other manager gives us a ground truth to check.

Do not start investor #2 until Berkshire reconciles.

---

## 5. BLOCKER: SEC is unreachable from the dev environment

Measured 2026-09-14, not assumed:

```
www.sec.gov:443    connect_rejected   (egress proxy, organization policy)
data.sec.gov:443   connect_rejected
```

Same situation as Yahoo Finance (`/CLAUDE.md` §3). **GitHub Actions runners are
not subject to this** — that is where Yahoo works today, and where the SEC probe
must run.

**Therefore: do not design the parser from memory.** First deliverable is a
`workflow_dispatch` probe that fetches one Berkshire filing on a runner and
uploads the raw response as an artifact, so the real shape can be read before any
parsing code exists. This project has a documented history of wrong guess-based
diagnoses (`/CLAUDE.md` §0).

Berkshire CIK: `0001067983`.

**Re-measured 2026-09-14 in a second session: identical.** `www.sec.gov:443` and
`data.sec.gov:443` both `connect_rejected` / gateway 403. Do not spend time
looking for a way around it from here — build for the runner.

### The probe now exists

```
scripts/probe_sec.py                fetch → measure → save raw. NOT a parser.
.github/workflows/probe-sec.yml     workflow_dispatch only, uploads sec-probe/
```

What it does, in order, saving every raw response:

```
A  data.sec.gov/submissions/CIK0001067983.json
B  the newest 13F-HR's folder index.json  (file names come from SEC, not from us)
C  every file in that folder under 8MB
```

Plus `manifest.json`: status codes, byte counts, content types, JSON top-level
keys, and a **tag census** for XML (tag name → count). The census is how the
position count and the field names arrive without anyone writing a parser first.
`--cik` / `--form` inputs make it reusable for investor #2.

**Tested against a local fixture server, not against SEC** (unreachable). Verified:
the happy path, a 404 on step A, a form that is not in `filings.recent`, an
oversized file being skipped, and that the contact address appears in **no** saved
file (`user_agent` in the manifest is written as the literal `<SEC_CONTACT>`).
The real shape is still unknown — that is the entire point of running it.

### 5-2. What run #1 actually returned (2026-09-14, measured)

```
A  data.sec.gov/submissions/CIK0001067983.json     200   161,265 B
B  .../Archives/edgar/data/1067983/000119312526352200/index.json
                                                    200       656 B
C  five files, all 200:
     primary_doc.xml                     5,555 B   42 tag kinds
     56757.xml                          44,724 B   15 tag kinds   ← the holdings
     0001193125-26-352200.txt           51,654 B   66 tag kinds   ← whole submission
     ...-index.html                      8,042 B   EDGAR's own rendering
     ...-index-headers.html              2,752 B   ditto
```

Newest 13F-HR: **filed 2026-08-14 for the quarter ending 2026-06-30**,
accession `0001193125-26-352200`. The 45-day lag is visible right there.

**SEC does not block the runner.** The declared-contact User-Agent is accepted;
no 403, no 418, no rate limiting at ~6 requests. Whole filing is ~51KB — §7's
"much smaller than it looks" holds.

#### The one finding that will bite anyone who guesses

**The holdings file has an arbitrary numeric name: `56757.xml`.** It is not
`infotable.xml`, not `form13fInfoTable.xml`, not anything predictable. **You must
read `index.json` to find it.** A parser that hardcodes a filename will work on
one filing and break on the next.

Worse, the obvious-looking shortcut is a trap: `filings.recent.primaryDocument`
in the submissions JSON says `xslForm13F_X02/primary_doc.xml` — that is an
**XSL rendering path for humans**, and it is the cover page, not the holdings.
Following `primaryDocument` gets you a filing with zero positions in it.

So the fetch order is fixed and non-negotiable:

```
submissions JSON  →  accessionNumber
accessionNumber   →  that folder's index.json
index.json        →  the .xml that is NOT primary_doc.xml
```

#### Still unread

The probe saved raw files as an artifact, but **the artifact cannot be downloaded
from this dev environment** — the download URL is on `blob.core.windows.net` and
the egress proxy 403s it (measured). Job logs ARE readable through the GitHub MCP
tools. So the probe now **prints the content into the log** (`--show`, default 3):
tag census per file, the first N repeating record blocks, and small files whole.
HTML files are counted only — they are EDGAR's rendering, not data.

That change is not yet run. **Next action is one more `Run workflow` click**, then
read the log and design the schema from what is printed.

---

## 6. ANSWERED — owner picked the address; secret still not set

SEC rejects anonymous requests; it requires a declared contact email in the
`User-Agent` header. **This repo is public**, so hardcoding the address exposes it
to scrapers.

Plan (mirrors how `TELEGRAM_TOKEN` is handled): read it from a repo secret.

```
Settings → Secrets and variables → Actions
  SEC_CONTACT   contact email declared to SEC
```

**ANSWERED 2026-09-14: the owner chose their own existing address** — the one
already on their GitHub/Umami account — over creating a project-specific one.
That is the explicit permission the global rule requires before their address
goes to an unrelated service, and it covers the SEC User-Agent, nothing else.

**Do not add it to the probe, a workflow, a default argument, or a doc example.**
It lives only in the `SEC_CONTACT` secret, which only the owner can set.

Honest caveat, found while writing this: **the address is already in the public
repo twice** — `/CLAUDE.md` §0 header and §5 (Umami account). So "nowhere in the
repo" is not true today. That does not change the rule for new code (a
User-Agent on every SEC request is a different exposure from one line in a doc,
and more instances is strictly worse), but nobody should claim the address is
unpublished. Told the owner 2026-09-14; removing those two lines is their call,
not ours. Nothing in `probe_sec.py` contains an address; it reads
`SEC_CONTACT` and refuses to run without it.

**The probe exits 1, not 0, when the secret is missing** — deliberately unlike
`notify.py`'s failure path and deliberately like its `--test` path. A probe is
run by hand, which means "confirm this works"; exiting 0 would leave a green run
that fetched nothing, and `/CLAUDE.md` §6-2 records that exact confusion actually
happening once.

Probe must exit with a clear message (not a crash) when `SEC_CONTACT` is empty,
matching `notify.py`'s behavior for missing secrets.

---

## 7. Data shape — much smaller than it looks

**Key insight, do not lose it.** Outcome tracking does not need a daily price
warehouse. It needs, per position:

```
price on the filing date   (quarter end)
price now
```

That is roughly `8 investors × ~30 positions × ~40 quarters ≈ 10k numbers`
— comparable to today's `market-long.json` (200KB). Daily series are needed only
if a single position gets its own chart, and then only for that ticker.

**This is another reason 8 investors is the right starting size.** 50 investors
means thousands of unique tickers, which does not fit one Actions run against
Yahoo's rate limits.

Reuse the existing pattern (`/CLAUDE.md` §3): Actions fetches → commits JSON to
the repo → the page reads only its own files. Browsers cannot call these APIs
directly (CORS).

---

## 7-2. URL: this page lives at `/titans/`, not at the site root

Owner decided 2026-09-14. One repo, one Pages site, three screens under one domain:

```
itpaidoff.com/            hub (not built yet — do NOT build it yet, see /CLAUDE.md §2)
itpaidoff.com/timing/     the existing dashboard (not moved yet)
itpaidoff.com/titans/     THIS project            ← build here from the start
itpaidoff.com/samuel/     DCA curves (rough idea)
```

**`titans`, not `masters`** — owner's word, chosen to avoid colliding with other sites
(and the golf tournament). **Lowercase**: paths are case-sensitive on Pages.

Building here costs nothing in SEO because the root is untouched. Do not move the
dashboard or create the hub as part of this project — the root page is currently the
only substantial content Google has, and it is still unindexed. Full reasoning in
`/CLAUDE.md` §2 "앞으로의 주소 구조".

## 8. Design — non-negotiable

**Read `/docs/design-system.md` before writing any markup or CSS.** That document
was extracted from the live `index.html` by measurement and exists specifically so
this project looks like the same site.

Highest-risk items for a new page:
- paper grid background (56px) — the signature that makes pages look related
- `var(--up)` / `var(--down)` only; **never literal color values** — they flip by
  language (ko/ja/zh: up=red, down=blue; else up=green, down=red)
- no rounded corners, no gradients, no colored buttons, no shadows except floating
- mono for numbers, condensed-uppercase for labels, Pretendard for sentences
- print the value next to the picture; do not make readers read a scale
- never phrase anything as "buy" — especially in English, where two independent
  external reviews caught exactly this drift

---

## 9. Required on-screen disclosures

```
45-day delay          this is a photograph of the past, not current holdings
US long equity only   shorts / bonds / FX / futures / foreign are invisible
not advice            same weight and size as body text, never fine print
```

Burry's page needs the staleness line more prominently (§3).

---

## 10. Legal

- 13F content itself: public domain, no license issue.
- **Do not put a living investor's name in a domain or brand.** Right of publicity
  and trademark. Using 13F data and putting someone's name on the sign are
  entirely different things. (`/CLAUDE.md` §9 도메인)
- **Assistant does not give legal advice.** State facts, let the owner decide
  (`/CLAUDE.md` §11).

---

## 11. Next actions, in order

```
1. DONE  SEC_CONTACT secret set by owner
2. DONE  probe built
3. DONE  run #1 — SEC reachable, shape summary in §5-2
4. Owner clicks Run workflow once more (probe now prints content to the log)
5. Read the log, THEN design the JSON schema
6. Build the fetch script + quarterly workflow
7. Reconcile against Berkshire's annual report. Do not proceed until it matches.
8. Build the page at /titans/ against /docs/design-system.md
9. Only then, investor #2
```

Steps needing a click are the owner's — assistants here cannot run Actions. Say
exactly which buttons: **Actions → Probe SEC → Run workflow**. Do NOT ask them to
download the artifact; read the job log instead (the artifact host is blocked here).

## 12. Working conventions for this repo

- Owner merges PRs by clicking green. Assistant branches, pushes, opens PRs.
- **Every handover states: PR number, commit count, what changes.**
- **After a merge, new work goes in a NEW PR.** Three separate incidents where
  commits were stacked onto an already-merged branch and never reached the site.
  `git fetch origin main` first, every time.
- Assistant cannot push tags (403, org policy). Use branches for backups.
- Never run `playwright install`; chromium is at
  `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.
- Verify by measuring, not by reasoning. This project has a long list of
  guess-based diagnoses that turned out wrong.
