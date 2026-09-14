# 대가들의 선택 (13F) — handover

> Agent-facing working doc. Written for a fresh session to resume this project
> in a different window. Dense on purpose; the repo owner does not need to read it.
> Prose language here is English for density — **all user-facing output and all
> conversation with the owner is Korean.** Owner is a non-developer: no terminal,
> no git. See `/CLAUDE.md` §0.

STATUS as of 2026-09-14: **probe built and merged-ready; it has never been run.**
Step 2 of §11 exists in code (`scripts/probe_sec.py`, `.github/workflows/probe-sec.yml`).
It cannot run until the owner adds the `SEC_CONTACT` secret (§6) — still the one
blocker. Nothing is parsed, no schema exists, no page exists. Everything below §4
is decided, not speculative.

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

---

## 6. OPEN — needs the owner's answer before the probe can run

SEC rejects anonymous requests; it requires a declared contact email in the
`User-Agent` header. **This repo is public**, so hardcoding the address exposes it
to scrapers.

Plan (mirrors how `TELEGRAM_TOKEN` is handled): read it from a repo secret.

```
Settings → Secrets and variables → Actions
  SEC_CONTACT   contact email declared to SEC
```

**Asked the owner on 2026-09-14 whether to use dysan1000@gmail.com or a different
address. Asked again on 2026-09-14 in a second session. Not yet answered.** Do not
put any email address in code before they answer — the global rule is that their
email is used only to identify them, never sent to an unrelated service unless
they explicitly ask. Nothing in `probe_sec.py` contains an address; it reads
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
1. Get the SEC_CONTACT answer, owner adds the secret     ← STILL BLOCKING
2. DONE (built, never run): workflow_dispatch probe
3. Owner runs Actions → Probe SEC → Run workflow.
   Download the sec-probe artifact. Read manifest.json first.
4. THEN design the JSON schema, from what the artifact actually shows.
5. Build the fetch script + quarterly workflow.
6. Reconcile against Berkshire's annual report. Do not proceed until it matches.
7. Build the page against /docs/design-system.md.
8. Only then, investor #2.
```

Step 3 is the owner's click, not ours — assistants here cannot run Actions. When
handing it over, say exactly which buttons: **Actions → Probe SEC → Run workflow**,
then the artifact at the bottom of the finished run.

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
