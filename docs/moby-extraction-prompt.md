# Moby.co Data Extraction — Comet Browser Prompt

> **Purpose**: Extract Moby analysis articles for all tickers in our 10 watchlists.
> **Output format**: One markdown file per weekly report, matching the format of the existing `2026-03-16 to 2026-03-22 Weekly Moby Report.md`.
> **Pace**: Read at human speed (~30 seconds per page) to avoid triggering anti-bot detection.

---

## Prompt for Comet Browser / Perplexity

```
I need to extract stock analysis articles from moby.co for a list of tickers.

IMPORTANT RULES:
- Browse at a natural human pace (wait 20-30 seconds between page loads)
- Do NOT make rapid sequential requests
- Read each article fully before moving to the next
- If you see a CAPTCHA or rate limit, STOP and tell me

For each ticker below, search moby.co for the most recent analysis article.
Extract the following fields into a structured markdown format:

### [TICKER] — [Company Name] | [Article Date]

Article Title: "[exact title]"
Rating: [Overweight/Equal-weight/Underweight]
Current Price: $[price] | Price Target: $[target] ([+/-X% upside/downside]) | Target Date: [date]
Market Cap: $[cap] | EPS: $[eps] | P/E: [ratio] | Upcoming Earnings: [date]

Thesis Summary:
[2-3 sentence summary of the investment thesis]

Why It's Winning/Losing:
- [bullet points]

Financials:
- [key financial metrics mentioned]

Opportunities:
- [bullet points]

Risks:
- [bullet points]

Moby Conclusion: [their closing statement]

---

TICKERS TO SEARCH (process in order, one at a time):

BATCH 1 — Tech Giants (13 tickers):
AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, CRM, ADBE, ORCL, NFLX, AMD, INTC

BATCH 2 — Semiconductors (18 tickers):
TSM, AVGO, QCOM, TXN, MU, MRVL, LRCX, AMAT, KLAC, ASML, ADI, ON, STX, WDC, NXPI, MCHP, SWKS, TEL

BATCH 3 — Moby Picks (top 20):
KMX, BKNG, COST, EFX, MCHP, LUMN, CTSH, CCJ, PWR, CDE, BWXT, PH, GRMN, ETN, SMCI, UBER, SQ, LI, ABNB, COF

BATCH 4 — Precious Metals:
SLV, GLD, NEM, GOLD, AEM, WPM, FNV, RGLD, AGI, KGC, BTG, HL, CDE, HMY, OR, MAG, SSRM, PAAS, SVM

BATCH 5 — Clean Energy:
ENPH, SEDG, FSLR, RUN, NOVA, NEE, BEP, AES, PLUG, BE, QCLN, TAN, ICLN, NLR

BATCH 6 — ETFs:
SPY, QQQ, DIA, IWM, VTI, ARKK, XLF, XLE, XLK, SMH, GDX, GDXJ, IAU, GLDM

BATCH 7 — S&P 500 (sample top 30):
JNJ, UNH, PG, HD, JPM, V, MA, PFE, ABBV, MRK, PEP, KO, TMO, ABT, DHR, BMY, LLY, AVGO, CSCO, ACN, TXN, QCOM, HON, LOW, CAT, DE, GE, RTX, BA, LMT

If moby.co does not have an analysis for a specific ticker, note it as:
### [TICKER] — No Moby analysis found

After completing each batch, compile the results into a single markdown file named:
`moby_analysis_batch_[N]_[date].md`

Total tickers: ~130 unique (after dedup across watchlists)
Estimated time at human pace: 65-90 minutes per batch of 20 tickers
```

---

## Post-Extraction

After the markdown files are extracted, run the parser to load into DuckDB:

```bash
# On the server or locally
python scripts/moby_to_duckdb.py moby_analysis_batch_1_2026-03-24.md data/sentimentpulse.db
python scripts/moby_to_duckdb.py moby_analysis_batch_2_2026-03-24.md data/sentimentpulse.db
# ... etc
```

The parser will deduplicate by (ticker, date) so re-running is safe.

---

## Notes

- Moby.co is a paid subscription service — only extract articles you have access to
- The extraction pace (20-30s per page) is critical to avoid account flags
- Not all tickers will have Moby analysis — smaller/non-US tickers likely won't
- SGX tickers (*.SI) almost certainly won't have Moby coverage
- Focus on US large-cap and mid-cap tickers first (Batches 1-3)
