# 대가들의 선택 (13F) — handover

> Agent-facing working doc. Written for a fresh session to resume this project
> in a different window. Dense on purpose; the repo owner does not need to read it.
> Prose language here is English for density — **all user-facing output and all
> conversation with the owner is Korean.** Owner is a non-developer: no terminal,
> no git. See `/CLAUDE.md` §0.

Historical snapshot as of 2026-09-14: **111 quarters committed, 1998-12-31 … 2026-06-30, no gaps.**
`SEC_CONTACT` is set; run #1 (2026-09-14, 12s) came back **200 on every request**.
Current implementation, measurements and unfinished work are recorded only in
`CLAUDE.md` §9-3-1, including the 2026-09-24 audit fixes. The dated sections below
retain the investigation history; they are not the current task list.

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

### DECIDED 2026-09-28 — the eight (owner's list; supersedes the lists below)

Owner grouped investors by **style** first, then picked so every style is covered.
The style label is descriptive, never a verdict, and becomes the grouping on the
future `/titans/` list page.

```
value        Warren Buffett / Berkshire Hathaway      built
value        Li Lu / Himalaya Capital                 Munger's manager; CN/HK names not in 13F
value        Seth Klarman / Baupost                   replaces Greenblatt (see below)
growth       Cathie Wood / ARK                        DEFERRED: ARK self-publishes daily; do last
distressed   Howard Marks / Oaktree                   DECIDED (probe run 3) — replaces Dalio
macro        Stanley Druckenmiller / Duquesne FO      macro; 13F = stock sleeve only
activist     Bill Ackman / Pershing Square            ~8-10 names
contrarian   David Tepper / Appaloosa                 options excluded; TWO CIKs stitched (below)
```

- **Dalio: owner override of the old rejection.** Owner: retirement is not the
  point — Buffett also stepped down (CEO → Greg Abel, end-2025); the page stands
  on *carrying the philosophy*. The T1 problem stays real (13F is mostly ETFs;
  macro bets in futures/FX/bonds are invisible), so his page must say plainly that
  13F shows the stock sleeve only. Same note for Druckenmiller.
- **Cathie Wood: owner wants her in**, reasoning her self-publishing is a plus, not
  a minus. Built **after** the 13F-only investors ("13F 밖에 방법이 없는 사람들만 우선").
- **Dropped from the 2026-09-14 list:** Burry (Scion deregistered Nov 2025, no new
  13F), Pabrai (13F nearly empty after moving to non-US markets), Terry Smith,
  Chris Hohn (reserve). Reserves: Seth Klarman, Carl Icahn, Chris Hohn.
- **Renaissance / Citadel: owner considered "top 30-50 only", then dropped both.**
  Not a load problem (top-50 fits), a meaning problem: Medallion holds for days so
  a quarter-end snapshot is noise; Citadel's long book is one half of hedged pairs
  and the short half is invisible. Do not re-propose.
- **Legends with no usable 13F** (owner asked): Graham (fund closed 1956), Fisher
  (small adviser, d.2004), Lynch and Neff (inside Fidelity / Wellington filings,
  not separable), O'Neil (own account + IBD; being checked by the probe).
  Greenblatt is the only one of that list still filing (dropped anyway, above).
- **Price file split: DONE (2026-09-28).** `data/titans/prices.json` stays the
  bot's shared store (one download per CUSIP however many investors hold it);
  `fetch_prices.py` then writes `data/titans/prices/<slug>.json` holding only
  that investor's latest holdings, and each page reads its own file
  (`window.TITAN.prices`). `--publish` rebuilds those files without downloading.
  Git growth measured: 7 daily versions of the 2.2MB file pack to 525KB, about
  one gzip copy, so daily rewrites are nearly free in history.

### Probe run 1 (2026-09-28, run 36369828081) — what it settled

```
             latest     issuers  top50   new/qtr(median)  ETF(name)
Li Lu        2026-06-30      7   100%        0.0%           0%
Greenblatt   2026-06-30  1,571    41%       10.6%          27%   → DROPPED
Dalio        2026-06-30    992    62%       18.7%          31%
Druckenmiller 2026-06-30    85    92%       46.2%           3%   total printed $0.0B
Ackman       2026-03-31     10   100%       10.0%           0%   Q2 filing missing
Tepper (new) 2026-06-30     25   100%       11.8%           7%
Tepper (old) 2015-12-31     47   100%       12.8%           2%
```

- All six CIKs matched the SEC entity names.
- **Greenblatt dropped → Seth Klarman (owner, 2026-09-28).** Gotham is a quant
  long/short book: 1,571 names, #1 is SPY at 19.8%, top 50 only 41%, shorts
  invisible — the Citadel problem again. Klarman CIK `0001061768` is from memory;
  the probe now lists Baupost and prints the SEC name — run it before registering.
- **Tepper: stitch both CIKs (owner).** Old `0001006438` (1999-2015, stopped) is a
  one-time fetch; weekly watching needs only new `0001656456`. Registry takes one
  CIK today, so this is either a registry field for frozen predecessor CIKs or a
  one-time merge into `appaloosa.json` — decide when building him.
  Owner asked first *why* the number changed (a different firm must not be
  stitched). Press reports: Jan 1 2016 reorganization when Tepper moved the firm
  from Short Hills NJ to Miami Beach FL (tax residency); manager entity became
  Appaloosa LP. The probe now prints a continuity block (old last quarter vs new
  first quarter: shared issuers, value kept each way, cover manager/city/signer,
  day gap). Stitch only if the book clearly carries over.
- **Druckenmiller: total printed $0.0B** (cover total too). Likely the filer still
  reports thousands after 2023-01-03, which the date-only `unit_scale` rule would
  misread by 1000×. Unconfirmed; probe now prints median value÷shares per filing.
  Needs a per-filing unit check before registering him.
- **Ackman: latest is 2026-03-31**; the Q2 filing (due Aug 14) was not in the list.
  Check EDGAR before registering.
- O'Neil: one hit, name not shown (search printed the atom author "Webmaster").
  Fixed: the probe now names every hit from its submissions file.

### Probe run 2 (2026-09-28, run 36375516285) — what it settled

- **Dalio DROPPED (owner)**; slot goes to **Howard Marks / Oaktree** if run 3 holds
  up (CIK `0000949509` from memory; core business is credit/distressed, so the 13F
  is the equity sleeve only — same page note as Druckenmiller).
- **Druckenmiller: all 85 issuers, no top-50 cut (owner).**
- **Klarman confirmed:** BAUPOST GROUP LLC/MA, 23 issuers, top 50 = 100%.
- **Thousands-unit filers after 2023:** median value÷shares Druckenmiller $0.09,
  Klarman $0.13 (cover totals equally small). The date-only `unit_scale` rule is
  wrong for them. Before registering either, add a per-filing unit check
  (e.g. implied price vs stored close, 1000× is unmistakable).
- **Tepper stitch confirmed:** old last 2015-12-31 (47 issuers, APPALOOSA
  MANAGEMENT LP, Miami Beach FL) vs new first 2016-03-31 (43, APPALOOSA LP, Short
  Hills NJ); same signer Michael L Palmer (CFO); 34 shared issuers; value carried
  87% / 85%; 91-day gap. Note the addresses run FL→NJ, opposite to the press-based
  guess written earlier.
- **Ackman Q2 still absent**, no other Pershing 13F filer in search. Run 3 prints
  the latest 13F-family forms (incl. 13F-NT) per CIK.
- O'Neil: `O'Neil Global Advisors, Inc.` (CIK 0001861159) — a firm, not his book; not added.

### Probe run 3 (2026-09-28, run 36376757948) — what it settled

- **Marks IN (owner).** OAKTREE CAPITAL MANAGEMENT LP, CIK 0000949509 confirmed.
  Latest 13F $7.2B: SH $3.8B (48 issuers, top 50 = 100%, median new/qtr 18%),
  options $1.9B, PRN $1.5B — the SH-only screen shows about half. Units normal
  (median value/shares $16.56). 66 amendments over 27 years.
- **Ackman Q2 2026 = 13F-NT** (filed 2026-08-14): his holdings were reported by
  another manager. The probe now reads the 13F-NT cover's otherManager block
  (name / 028- file number / CIK). Do not register him until that filer is known.
- Klarman/Druckenmiller thousands confirmed again. **Fixed in the collector:**
  `fetch_13f.unit_by()` compares each filing's value/shares with the same CUSIPs'
  prices in the previous stored quarter; flips the date rule only when the date
  reading is >100x off and the other unit is within 10x (≥3 shared names), else
  follows the previous same-era quarter's unit, else the date rule. Records
  `unit_by` on the quarter when it overrides. Berkshire's 110 consecutive pairs
  read identically (test). Price level alone still never decides the unit.
- **Verify first:** `scripts/probe_titans.py` + `probe-titans.yml` (manual). CIKs
  in it are from memory; it prints the SEC entity name next to each.

### Tepper registered (2026-09-28)

- `appaloosa`, CIK 0001656456, `since 2013`, `predecessors: [0001006438]`.
  `fetch_13f.list_filings()` walks the current CIK then each predecessor; a
  predecessor filing is kept only if its period precedes the current CIK's first
  13F-HR. `ACC_CIK` maps accession -> filer CIK so `filing_docs()` builds the
  archive path under the filer's own CIK. Quarters from the old CIK carry
  `filer_cik`; the book's `manager.predecessors` lists the old CIKs.
- 1999–2013Q1 under the old CIK are text filings: not converted (one-time rule).
- Test: `PredecessorTests` in `test_fetch_13f.py` (reverting the folder or the
  overlap rule each fails it).

### Marks registered (2026-09-28)

- `oaktree`, CIK 0000949509, filing name `Oaktree Capital Management LP`, `since 2013`.
  No predecessors. SH-only screen shows about half of the 13F (options and PRN excluded);
  the bio and list card say so without numbers. 66 amendments: an unknown
  `amendmentType` keeps the weekly run red until a person looks (by design).

### Klarman registered (2026-09-28)

- `baupost`, CIK 0001061768 (probe 2: BAUPOST GROUP LLC/MA), filing name
  `Baupost Group LLC`, `since 2013`. Files in thousands after 2023 (median
  value/shares $0.13); `unit_by()` flips it against the previous stored quarter,
  same path that fixed Li Lu's six quarters. Bio/card say US-listed shares only
  (distressed debt, real estate, private deals are outside the 13F).
- Quote: Margin of Safety (1991), the margin-of-safety definition, checked
  against several book summaries; 1982 co-founding checked (Wikipedia, CNBC).

### Probe run 4 (2026-09-28, run 36377898009)

- **Ackman 13F-NT reporting manager:** PERSHING SQUARE INC., CIK 0002026053,
  028-25746. Next: probe that CIK's 13F-HR (does it hold only Pershing's book?
  names continuous with CIK 0001336528's last 13F-HR 2026-03-31?) — same test as
  the Tepper stitch. Not registered until then.
- Li Lu confirmed: 35 13F-HR since 2016-12-31, 1 amendment (2025-12-31), units
  normal ($289 median), 7 issuers, 80% in 3. **Registered** as `himalaya`; page
  at `titans/himalaya/`. Data arrives on the first Update 13F run after merge.
- `fetch_prices.main()` skips a registered investor with neither a book nor a
  `prices/<slug>.json` (never collected); a missing book with a projection still
  stops (strict). Test: `test_a_just_registered_investor_waits_but_a_lost_book_still_stops`.

### Accepted — first eight (2026-09-14; superseded above, kept for the reasoning)

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

### 5-3. Run #2 — the actual 13F shape (2026-09-14, read off the log)

`56757.xml`, root `<informationTable>`, namespace
`http://www.sec.gov/edgar/document/thirteenf/informationtable`. **89 `<infoTable>`
records.** One record:

```xml
<infoTable>
  <nameOfIssuer>ALLY FINL INC</nameOfIssuer>
  <titleOfClass>COM</titleOfClass>
  <cusip>02005N100</cusip>
  <value>577211815</value>
  <shrsOrPrnAmt><sshPrnamt>12561737</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
  <investmentDiscretion>DFND</investmentDiscretion>
  <otherManager>4</otherManager>
  <votingAuthority><Sole>12561737</Sole><Shared>0</Shared><None>0</None></votingAuthority>
</infoTable>
```

Census is exact: every one of `nameOfIssuer, titleOfClass, cusip, value,
shrsOrPrnAmt, sshPrnamt, sshPrnamtType, investmentDiscretion, otherManager,
votingAuthority, Sole, Shared, None` appears **89×**. So every field is present on
every row, and **`putCall` does not appear at all** — Berkshire held no options
this quarter. It exists in the schema; a parser must tolerate its absence AND
its presence.

`primary_doc.xml` (cover page) gives the metadata worth keeping:

```
periodOfReport / reportCalendarOrQuarter   06-30-2026
isAmendment                                false
filingManager.name                         Berkshire Hathaway Inc
signatureDate                              08-14-2026
otherIncludedManagersCount                 14
tableEntryTotal                            89
tableValueTotal                            299253556246
isConfidentialOmitted                      false
otherManagers2Info                         14 × {sequenceNumber, form13FFileNumber, name}
```

#### THE finding: 89 rows ≠ 89 positions

The first three records are **all ALLY FINL INC, all CUSIP `02005N100`**, differing
only in `otherManager` (`4` / `2,4,11` / `4,5`) and amount. Berkshire files on behalf
of itself plus 14 subsidiaries (GEICO, General Re, National Indemnity, … and
`Buffett Warren E` is sequence 4), and **each subsidiary combination gets its own
row.**

```
577,211,815 + 128,838,056 + 194,285,790  =   900,335,661   ← real Ally position
 12,561,737 +   2,803,875 +   4,228,200  =    19,593,812   shares
```

**Any screen built off raw rows shows Ally three times.** Group by `cusip` and sum
`value` and `sshPrnamt`. `tableEntryTotal` counts rows, so it is not a position
count and must never be shown as one. `otherManager` is a comma-separated list of
`sequenceNumber`s pointing into `primary_doc.xml`'s `otherManagers2Info` — useful
if we ever want "which subsidiary held it", useless otherwise.

#### Units: dollars, verified by arithmetic

All three Ally rows give `value / sshPrnamt` = **exactly 45.95**. That is a share
price, so `value` is in **dollars**, not thousands. `tableValueTotal`
299,253,556,246 = $299.25B agrees.

**Do not assume this held historically.** SEC changed the units at some point; a
filing reported in thousands would render old quarters 1000× too big. Do not
hardcode a cutover date from memory — run #3 fetches the oldest filing in
`filings.recent` so the two ends can be compared directly. Better still, the
fetcher should **self-check**: `value / sshPrnamt` must land in a plausible
share-price range, else the filing is in thousands.

#### Other notes

- `.txt` (the complete submission) contains both documents wrapped in SGML, so one
  fetch could replace two. Not worth it — `index.json` + the XML is cleaner and the
  census proved the `.txt` carries `otherManager×103` (89 rows + 14 cover entries),
  which is exactly the kind of double-count that causes bugs.
- `<ccc>` in the cover page is masked `XXXXXXXX` by EDGAR. Nothing sensitive.
- `schemaVersion` X0202. Worth storing — old filings will differ.

### 5-4. Run #3 (queued, one click) answers what is left

The probe now also prints **every 13F-HR in `filings.recent`** (filing date, report
date, accession, size) plus the count of older `filings.files` chunks, and then
fetches **the oldest one in recent** so its units and field set can be compared
against the newest. `--no-old` turns that off.

Open questions it closes: how many quarters are reachable without paging into
`filings.files`, and whether the schema/units shifted.

### 5-5. Known unsolved: CUSIP → ticker

13F gives **CUSIP only**. Yahoo needs tickers. SEC's `company_tickers.json` is keyed
by CIK, not CUSIP, and 13F does not carry the issuer's CIK. Options, none free of
cost:

```
hand-built table      ~50 names for Berkshire. Verifiable, and the annual-report
                      reconciliation (§4) checks it. Does not scale to 8 investors.
OpenFIGI API          free, maps CUSIP→ticker, rate-limited without a key.
```

**Start with the hand-built table** — Berkshire only, checked against the annual
report. Revisit before investor #2. Do not let this block the fetcher: store `cusip`
as the key in the JSON and treat `ticker` as an annotation that can arrive later.

### 5-6. Run #3 — history depth and the units change, both settled

```
13F-HR in filings.recent    39, covering 2016-12-31 … 2026-06-30
filings.files chunks        1   (older history, fetched too — script handles it)
```

**The units DID change, and it is confirmed by arithmetic, not memory:**

```
2026-06-30  56757.xml             value/shares = 45.95     → dollars
2016-12-31  form13fInfoTable.xml  value/shares =  0.0467   → thousands
                                  ×1000 = 46.69  ← real Dec-2016 AAL price

tableValueTotal 2016 = 147,985,198
  read as dollars   → $148 million   absurd for Berkshire
  read as thousands → $148 billion   correct
```

**And the filename differed across the two filings** (`56757.xml` vs
`form13fInfoTable.xml`), which is the §5-2 finding confirmed on a second sample
rather than inferred from one.

Row counts: 148 rows in 2016-12-31 vs 89 in 2026-06-30. Field set identical
(same 15 tags, each appearing exactly `rows`×). The old cover page carries three
extra flags (`confirmingCopyFlag`, `returnCopyFlag`, `overrideInternetFlag`);
harmless. `schemaVersion` is absent in the 2016 cover page and `X0202` in 2026.

### 5-7. The fetcher (`scripts/fetch_13f.py`) — built on those three findings

Writes `data/titans/berkshire.json`. **No prices yet** — reconcile totals first
(§4), then solve CUSIP→ticker (§5-5).

```
list_filings()   recent + every filings.files chunk → all 13F-HR, oldest first
holdings_xml()   read index.json, take the LARGEST .xml that is not
                 primary_doc.xml. Never a hardcoded name, never primaryDocument.
unit_scale()     uses the submission date under the SEC format rule; median
                 value/shares is diagnostic only. See CLAUDE.md audit follow-up.
fold()           group by (cusip, class, sshPrnamtType, putCall), sum value and
                 shares, keep `lines` = how many rows collapsed.
```

Stored shape, values always USD:

```json
{"updated","source","manager":{"cik","name"},"note",
 "quarters":[{"period","filed","accession","lines","unit","total",
              "holdings":[{"cusip","name","class","value","shares","lines"}]}]}
```

`unit` records what was detected so the decision stays auditable; `lines` on both
levels keeps the row-vs-position distinction visible rather than silently erased.

Incremental: filings are immutable once filed, so any accession already in the
JSON is skipped. A quarterly run costs ~3 requests. Guards, all exercised against
a fixture server: missing `SEC_CONTACT` → exit 1; submissions unreachable → exit 1
and **the existing file is left untouched** (same principle as `fetch_long.py`,
`/CLAUDE.md` §3); one quarter 404ing → the others still save and that quarter
backfills on the next run.

Unit-tested with the **real numbers read off the probe logs** — the three Ally
rows fold to 900,335,661 / 19,593,812 shares, and the 2016 rows scale to a
$46.69 AAL price. SH / PRN / Put are kept separate, never summed together.

The original workflow was weekly. The multi-investor watcher described in §10-1
now checks each current SEC submission list twice on weekdays and runs the heavy
collector only when an accession is new. Sunday remains the full safety check.

#### Historical decision before 2026-09-20: amendments were not merged

Superseded by the XML amendment merger documented in `CLAUDE.md` §9-3-1.
The following records the original reasoning, not a present-day restriction.

The fetcher matches `13F-HR` exactly, so amendments are skipped. **This is a
decision, not an oversight.** An amendment can be either a *restatement* (replaces
the original table entirely) or an *addition* (carries only the rows that were
missing, often previously under a confidential-treatment request). Treat one as
the other and a quarter either doubles or empties. No sample has been seen, so
there is nothing to design against.

Rather than guess, `list_filings()` **counts and prints them** on every run
("정정 공시(13F-HR/A) N건" or "없음"). So the first real run answers whether
Berkshire has any at all. When one shows up: probe that accession, read its cover
page (`amendmentType` / `isAmendment` / `amendmentNo` in the `coverPage`), and only
then decide the merge rule. Until then a quarter with an amendment silently uses
the original numbers — acceptable for now, but it is a known inaccuracy, not a
clean state.

**Not yet run against real SEC.** Next: one `Run workflow`, read the log, check
the printed totals per quarter against Berkshire's annual report (§4).

### 5-8. First real run (2026-09-14) — what actually came back

```
13F-HR found          111, 1998-12-31 … 2026-06-30
saved                  53, 2013-06-30 … 2026-06-30     data/titans/berkshire.json, 273 KB
13F-HR/A found        100  ← not 0. See below.
```

**The unit switch is real and lands on exactly one boundary:**

```
2022-09-30   value/shares 0.06   thousands
2022-12-31   value/shares 63.61  dollars     ← one clean cutover, no mixed quarter
```

Totals look right across the whole range ($89B in 2013 → $299B in 2026), and
2016-12-31 came out at **$148.0B**, matching what §5-6 predicted from that
filing's own `tableValueTotal`. Folding is lossless: summing each holding's
`lines` equals the raw row count in **all 53 quarters**.

#### Two things the run exposed

**(a) 58 "failures" were not failures.** Every 13F-HR from 1998-12-31 through
2013-03-31 has **no XML in its folder at all** — EDGAR did not require XML for
13F until mid-2013, so those filings are text documents in a different format.
Counting them as failures means every weekly run prints 58 errors forever, and
**a real failure would be invisible inside that noise.** They are now counted
separately (`NO_XML`) and reported as "XML 이전 형식이라 건너뛴 분기".

Pre-2013 history needs a separate text parser. **The owner pushed back on
dropping it (2026-09-14): "우리 사이트는 데이터가 생명인데." They are right that
2008 is the single most valuable stretch for a site about how choices turned
out** — Buffett's 2008 moves are the story. So this is not closed, it is
**unmeasured**, and the next step is to look rather than to argue.

What is actually known vs. assumed:

```
KNOWN    index.json returns 200 for these filings; the folder simply has no .xml
KNOWN    ~90 of the 100 amendments fall in this pre-2013 era — much messier
UNKNOWN  what the documents look like: fixed-width text? HTML tables? both?
UNKNOWN  whether the format is stable, or changes with the filing agent
```

The filing-agent prefix changes across the era (`0000950150` → `0000950129` →
`0000950134` → `0000950123` → `0001193125`), and filing agents are exactly the
kind of thing that changes a text layout. **Do not write one parser on the
assumption of one format.**

`probe_sec.py --accession` takes a comma-separated list for this. Three samples
span the era:

```
0000950150-00-000118   oldest (1998-12-31 era)
0000950134-09-003064   2008 year-end era
0001193125-13-222307   last pre-XML (2013-03-31)
```

For text filings the probe now dumps `--head` characters (default 8000) instead
of counting tags, and — because the SGML header can be long enough to push the
table past that window — `table_peek()` finds the first CUSIP-shaped token and
prints from just before it. Measured: on a fixture with an 11KB header it lands
on the table. That is locating, not parsing.

#### DECIDED 2026-09-14: this is a one-shot conversion, not a parser

Owner: **"어차피 한번만 할건데, 파서까지 만들 일이야? 그냥 니가 요즘 형식으로
정리해주면 되잖아."** Correct, and it reframes the job. These 58 filings are
frozen forever. Nothing needs to run weekly, recover from errors, or handle a
format we have not seen. **Write throwaway code, verify it, commit the JSON,
delete the code.** Do not build a maintained pre-2013 pipeline.

The obstacle was never the parsing, it was *seeing* the files:

```
SEC blocked from the dev environment       → cannot fetch directly
58 × ~90KB ≈ 5MB                           → too large to read through job logs
artifact download on blob.core.windows.net → proxy 403
```

**Solution: the runner pushes the raw filings to a scratch branch**
(`scripts/dump_13f_raw.py` + `.github/workflows/dump-13f-raw.yml`, branch
`raw-13f`). The assistant then fetches that branch and reads the documents
locally, at full fidelity, with no click-and-wait loop. 13F is public domain, so
a public branch is fine. Amendments are dumped too — ~90 of the 100 are in this
era, so their shape gets settled in the same pass.

The branch is an **orphan** branch: it carries only `sec-raw/`, never main's
files. Verified on a scratch repo — `raw-13f` contains only the dump and `main`
is untouched.

**The conversion has a built-in answer key.** Each filing states its own
`Form 13F Information Table Value Total` and entry count. Crude extraction is
fine as long as every quarter reconciles against its own stated total — the same
check `fetch_13f.py` already does for the XML era (§5-8c). 58/58 matching means
done, regardless of how ugly the code was.

**Cleanup is part of the job**: once `berkshire.json` carries the old quarters,
delete `dump_13f_raw.py`, `dump-13f-raw.yml`, and the `raw-13f` branch. Leaving
them makes the next session think there is a pipeline to maintain.

**(b) 100 amendments exist, and ~7 fall inside the saved range:**

```
2013-06-30  2014-09-30  2015-06-30  2020-09-30
2023-09-30 (two)  2023-12-31  2025-03-31
```

These are almost certainly confidential-treatment releases — Berkshire routinely
asks the SEC to withhold a position while it is still building it, then files an
amendment once the position is complete. **That means those quarters' original
filings are genuinely incomplete**, not merely restated. This is no longer a
theoretical gap.

Still not merged, because the merge rule is still unknown (restate vs. add,
§5-7). Quarters with an amendment now carry `amended_by: [accession]` in the JSON
so the screen can mark them rather than quietly showing short numbers.
`probe_sec.py --accession` (and the workflow input) exists to open one:
**`0000950123-25-008361`** (2025-03-31, filed 2025-08-14) is the freshest sample.

#### (c) A self-check that beats eyeballing

Our summed total is now compared against the filing's own `tableValueTotal`
(scaled by the same factor), and the row count against `tableEntryTotal`. A
quarter off by more than 0.5% gets `total_mismatch` in the JSON and a `※` in the
log. This is the check that proves no rows were dropped and the unit call was
right — **it is not an independent check against the annual report**, since both
numbers come from the same filing. A true outside check still needs the annual
report, which is not reachable from this environment.

#### (d) Same issuer, two rows, both correct

`ALPHABET INC` appears twice in 2026-06-30 — CUSIP `02079K305` (CAP STK CL A,
$28.16B) and `02079K107` (CAP STK CL C, $9.61B). Different share classes are
different securities and must not be folded together. **The screen has to show
`class`, not just `name`**, or it will look like a duplicate row.

### 5-9. DONE — pre-2013 converted, 28 years of history in the file

The one-shot conversion ran. `data/titans/berkshire.json` now holds **111 quarters,
1998-12-31 through 2026-06-30, with no missing quarter.** 478 KB.

```
58 pre-2013 quarters converted from text; ALL 58 reconcile against their own
stated Form 13F Value Total.  (2 have a ±1 row-count difference with the money
exact — recorded as lines_mismatch, harmless.)
53 XML-era quarters: 0 total mismatches, confirmed on a second run.
```

2008 is in, which was the whole point:

```
2007-12-31 $68.8B → 2008-12-31 $51.9B → 2009-03-31 $40.9B → 2009-09-30 $56.5B
```

#### The five traps the text format actually had

Each surfaced because the money did not reconcile — never by reading the code.

```
TORCHMARK / SPONSORED    9-letter names matched as CUSIPs
greedy regex             ate the first digit of the value column (2,912,308 → 912,308)
right-aligned numbers    a wider value starts earlier, so align on the END not the start
868168 10 F / 82028k     check digit can be a LETTER, and lowercase appears
Entry Total:.            a period after the colon in the 2011 layout
```

The last two cost exactly two rows in 2000-09-30, and their sum was exactly the
gap. That is what a checksum buys you.

#### What was deleted, deliberately

`scripts/dump_13f_raw.py` and `.github/workflows/dump-13f-raw.yml` are **gone** —
they were one-shot scaffolding and leaving them would make the next session think
there is a pipeline here. **The `raw-13f` branch should be deleted too** (GitHub →
Branches → trash); it was 6.5 MB of raw filings and has served its purpose.

`scripts/onetime/convert_13f_text.py` is kept, clearly marked as run-once, **only**
so the old numbers can be audited later. Do not maintain it, do not re-run it.

#### Historical open items from the one-time text conversion

Current XML amendment handling and intentional pre-XML limitations are in `CLAUDE.md`.

- **At this stage amendments were not merged.** 85 were converted and 83 reconcile, but the
  merge rule (restate vs. add) is unused. Good news: the old paper form has explicit
  checkboxes — `This Amendment ... [ ] is a restatement. [ ] adds new holdings
  entries.` — so **the filing declares its own type** and the rule can be read
  rather than guessed. Affected quarters carry `amended_by`.
- File is 478 KB and will grow. If the page feels slow, split per-decade rather
  than dropping history.

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

## 7-2. URL: `/titans/berkshire/` — one folder per investor

Owner decided 2026-09-14. One repo, one Pages site, three screens under one domain:

```
itpaidoff.com/            hub (not built yet — do NOT build it yet, see /CLAUDE.md §2)
itpaidoff.com/timing/     the existing dashboard (not moved yet)
itpaidoff.com/titans/            investor list    ← build only when there are 2+
itpaidoff.com/titans/berkshire/  THIS project     ← here
itpaidoff.com/samuel/     DCA curves (rough idea)
```

**`titans`, not `masters`** — owner's word, chosen to avoid colliding with other sites
(and the golf tournament). **Lowercase**: paths are case-sensitive on Pages.

**Moved from `/titans/` to `/titans/berkshire/` on 2026-09-16** (owner's suggestion).
One folder per investor; `/titans/` is now a bounce page (canonical + refresh +
a *visible* link, and it carries `?lang=` through). Pages cannot do 301s, so the cost
of moving scales with how known the URL is — right now that is one sitemap line and
no index entry, so this was the cheapest possible moment.

**`berkshire`, not `warren-buffett`.** §10 and `/CLAUDE.md` forbid putting a living
investor's name on the signage (publicity/trademark). The 13F filer is the company,
not the man. stockcircle uses `/portfolio/warren-buffett`; do not copy that.

**Do not turn `/titans/` into a list page yet** — a two-link page is thin, and the site
is still unindexed. Build the list when investor #2 exists.

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

### 10-1. Multi-investor automation (2026-09-19)

Keep these pieces separate. A future fix to SEC transport, scheduling, investor
metadata, or filing parsing must not require copying the whole pipeline.

```
data/titans/investors.json   one validated list of active managers
scripts/titans/registry.py   validates that list and opens their saved books
scripts/titans/sec.py        SEC transport + pure recent-list parser
scripts/watch_13f.py         compares accessions and dispatches changed managers
scripts/fetch_13f.py         collects and validates one selected manager
update-13f.yml               schedule, commits, auxiliary jobs, Telegram
```

The weekday runs request only `submissions/CIK##########.json` once per active
manager. A new regular filing or amendment accession selects that manager for the
full historical-list/filing collector. Sunday and manual runs select every manager
as a safety check. One manager failing does not prevent another manager's good file
from being committed; the job still fails and sends the tail of the collection log
through the existing Telegram channel.
Ticker/SIC fetch or save failures keep the 13F commit but send a separately named
Telegram alert, so an auxiliary outage is not reported as a filing failure.

Ticker, SIC-sector, and daily-price collectors require all active books named by
the registry. Therefore a newly disclosed CUSIP joins those shared caches without
a Berkshire-specific code change. A manager still needs one registry entry, its
thin page with unique static SEO, and a sitemap row. Pre-2013 text conversion is a
per-manager one-time job, not part of recurring automation. Fetch the frozen
filings, use throwaway conversion code, verify quarters/rows/totals, commit the
JSON, and retain only the validation and format notes. Do not build or maintain a
shared pre-2013 parser. Current amendment processing is documented in `CLAUDE.md`.

---

## 11. Historical build checklist (current handoff: CLAUDE.md and worklogs)

```
1. DONE  SEC_CONTACT secret set by owner
2. DONE  probe built
3. DONE  run #1 — SEC reachable, shape summary in §5-2
4. DONE  run #2 — full 13F shape read off the log (§5-3)
5. DONE  run #3 — 39 quarters in recent + 1 older chunk; units change confirmed
6. DONE  schema designed (§5-7) — folded by CUSIP, units self-checked
7. DONE  fetch script + weekly workflow, unit-tested on fixtures
8. DONE  first real run — 53 quarters committed (§5-8)
9. DONE  self-check confirmed: 0 total mismatches
10. DONE  pre-2013 converted — 111 quarters, no gaps (§5-9)
11. DONE for XML amendments; intentional pre-XML gap is documented in CLAUDE.md
12. DONE  CUSIP→ticker (OpenFIGI + SEC name match), sectors (SEC SIC)
13. DONE  page shipped at /titans/berkshire/ — holdings list + per-holding chart
14. See 11; do not restart recurring pre-2013 parsing
15. DONE  registry + lightweight multi-investor watcher + shared dispatch
16. Per new manager, if needed: one-time verified pre-2013 conversion; do not automate
```

### Per-holding chart (2026-09-16)

Expanding a row draws that holding's whole life: **quarter-end price on top,
shares bought/sold that quarter below, shared x-axis.** It needs **no new data
source** — the price is `value ÷ shares`, the same implied price the cost-basis
estimate already uses, so the weekly 13F workflow refreshes the chart for free.
That property is worth protecting: it is the reason this product stays
public-domain and self-updating (§1).

Two traps, both found by measuring:

- **Splits must adjust the previous share count too**, not just the earlier
  points. Adjusting only the history made Apple's 2020 4:1 split render as a
  `+699M` purchase — the single largest bar in the chart. With `held` scaled,
  it reads `-36M`, the real trim. Same failure mode as the cost-basis bug in §7.
- **`text-anchor` must be an SVG attribute, not CSS.** A class rule beats the
  attribute, so the leftmost year label stayed centre-anchored and was clipped.

A holding that was never traded in the filing window (Coca-Cola, 111 quarters)
drops the lower panel entirely and says so in words. An empty panel with a lone
zero rule reads as a broken screen.

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
