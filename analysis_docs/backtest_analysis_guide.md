# Backtest Analysis Guide for Mid-term Stock Planner

A comprehensive guide to understanding and interpreting backtest results, metrics, and stock ranking outputs for your mid-term investment strategy.

---

## Part 1: Understanding Backtest Summary Metrics

When you run a backtest, you get high-level performance numbers. Here is what each one means and how to read it.

### 1.1 Return (Total Return %)

**What it is:**
- The total profit or loss as a percentage of your starting capital over the entire backtest period.
- Formula: `(Ending Value âˆ’ Starting Value) / Starting Value Ã— 100%`

**How to read it:**
- **+12% return** means if you started with $100, you ended with $112.
- Positive is good, negative means you lost money.
- But return alone is misleadingâ€”you also need to know how bumpy the ride was.

**Example from your run:**
- Your backtest returned **+12%**, which is reasonable if this ran over 1â€“3 years.
- But compare to what you could have gotten by just holding the S&P 500 or a benchmark ETF in the same period. If the benchmark did +10%, your +12% is only a modest +2% outperformance (and that's before costs).

**Red flags:**
- Single-year backtest with +12% may be cherry-picked or lucky.
- Multi-year backtest (5+ years) with +12% is more believable but still modest.

---

### 1.2 Sharpe Ratio

**What it is:**
- Measures **risk-adjusted return**: how much extra return you earned per unit of volatility (bumpy-ness).
- Formula: `(Portfolio Return âˆ’ Risk-Free Return) / Portfolio Volatility`
- Higher Sharpe = better risk-adjusted performance.

**How to read it (common benchmarks):**

| Sharpe Range | Interpretation | Confidence |
|---|---|---|
| < 0.5 | Weak; strategy not adding much value | Low |
| 0.5 â€“ 1.0 | Below average; consider improving | Moderate |
| 1.0 â€“ 1.9 | Good; respectable risk-adjusted performance | High |
| 2.0 â€“ 2.9 | Very good; hard to sustain live | Very High |
| â‰¥ 3.0 | Excellent; be skeptical if sample is short | Extreme (watch for overfitting) |

**Example from your run:**
- Your backtest Sharpe is **0.11**, which is very low.
- This means you earned only 0.11% extra return for each 1% of volatility you took on.
- Translation: your portfolio was quite bumpy (volatile) relative to the modest 12% gain.
- For context, a 60/40 stocks/bonds portfolio typically has a Sharpe around 0.5â€“0.8; your 0.11 is weaker.

**Why your Sharpe is low (diagnostic):**
- Mix of high-volatility picks (semiconductors, nuclear ETFs, volatile tech like AMD, MU) alongside lower-volatility blue chips.
- If equal-weighted, the noisy names dominate risk without proportional return.
- Sentiment and fundamental scores are moderate, suggesting no major edge to justify the risk.

**Action if Sharpe is too low:**
- Add volatility-weighted position sizing (smaller bets on risky names).
- Improve model to pick less risky names or stronger conviction names.
- Reduce position count and focus on highest-conviction picks only.

---

### 1.3 Win Rate (%)

**What it is:**
- Percentage of rebalance periods (months) where your portfolio beat the benchmark.
- Formula: `(Periods where Portfolio Return > Benchmark Return) / Total Periods Ã— 100%`

**How to read it:**
- **56.63% win rate** means your portfolio outperformed in about 57% of months, lost in about 43%.
- Slightly better than a coin flip (50%), but not strong evidence of edge.

**Common benchmarks:**
- Below 50% = strategy is consistently losing; reject it.
- 50â€“55% = barely better than luck.
- 55â€“60% = weak but possible signal.
- 60â€“70% = moderate edge; worth investigating.
- 70%+ = strong edge; be suspicious of overfitting unless out-of-sample.

**Example:**
- Your 56.63% means in roughly 5â€“6 months of every 10, you beat the benchmark; in the other 4â€“5, you didn't.
- Combined with Sharpe 0.11, this suggests you're barely outperforming when you do, and underperforming when you don't.
- The wins are probably small, the losses are comparable in size, so the net effect is modest +12%.

**Diagnostics:**
- Is win rate consistent across years, or did you win all the time in 2023 and lose all the time in 2025?
- If clustered, your strategy may be regime-dependent (works in bull markets, fails in bear markets).

---

### 1.4 Maximum Drawdown

**What it is:**
- The largest peak-to-trough decline your portfolio experienced during the backtest.
- Formula: `(Lowest Portfolio Value âˆ’ Highest Portfolio Value Before It) / Highest Portfolio Value Ã— 100%`
- Always reported as a negative number: â€“15% means you lost 15% from peak to trough.

**How to read it:**
- **â€“15% max drawdown**: if your portfolio peaked at $100, the lowest it went was $85.
- Longer backtests tend to have larger drawdowns (more market stress events).
- Sharper declines feel worse psychologically even if the magnitude is the same.

**Common benchmarks:**
- Below â€“10%: very good; rare unless strategy is defensive.
- â€“10% to â€“20%: typical for equity strategies; reasonable.
- â€“20% to â€“40%: high drawdown; requires strong conviction and long holding horizon.
- Above â€“40%: severe; most investors abandon strategies at this point.

**Example:**
- If your backtest had a â€“20% max drawdown (not shown in your summary), combined with +12% return and Sharpe 0.11:
  - You lost 20 cents for every dollar to get a 12% gain.
  - The pain-to-gain ratio is poor; Sharpe reflects this.
  - For a mid-term, "balanced" investor, you'd probably prefer a strategy with +10% return and â€“10% max DD over +12% and â€“20% DD.

**Check against your tolerance:**
- Ask yourself: "If my portfolio dropped 20%, would I stick with it, or would I panic-sell?"
- If you'd sell, the strategy is not suitable even if backtests look good.

---

### 1.5 Annualized Return (CAGR) vs. Volatility (Annualized Std Dev)

**Annualized Return (CAGR):**
- Compound Annual Growth Rate: the steady annual rate of growth if compounded over the whole period.
- More realistic than total return for comparing strategies of different lengths.

**Example:**
- 3-year backtest with +36% total return â‰ˆ +10.7% CAGR.
- 1-year backtest with +12% total return = +12% CAGR.
- The 3-year strategy is less impressive when annualized.

**Annualized Volatility (Std Dev):**
- Annualized standard deviation of daily/monthly returns; measures how much returns bounce around.
- Higher volatility = bumpier ride, even if average return is the same.

**Sharpe is the ratio:**
- Sharpe = CAGR / Annualized Volatility (roughly).
- If CAGR = 12% and Annualized Vol = 110%, then Sharpe â‰ˆ 0.11 (matches your result!).
- This tells you the volatility is very high relative to the return.

---

### 1.6 Turnover

**What it is:**
- Average fraction of portfolio that gets rebalanced each period (month).
- Formula: `Average |Weight Change| across all positions per rebalance / 2`
- Reported as % or as a decimal (e.g., 0.30 = 30% turnover).

**Why it matters:**
- Each trade has costs: bidâ€“ask spread, commissions, taxes (if applicable), and market impact for large positions.
- High turnover = high costs = net return looks worse in practice than in backtest.

**Common benchmarks:**
- Below 10% monthly turnover: conservative, low costs.
- 10â€“30% monthly: moderate; typical for factor/tactical strategies.
- Above 50% monthly: high; costs can eat 2â€“5% of returns annually.

**Example:**
- If your backtest assumes 0% costs and shows +12% with 40% monthly turnover:
  - In reality, trading costs might take 1.5â€“3% annually.
  - True net return: +9â€“10.5%, not +12%.
  - This is why backtests always overestimate live performance.

**Check in your backtest:**
- Your CLI should report turnover. If it shows 30% average monthly, costs are moderate.
- If above 50%, consider reducing the number of holdings or portfolio churn constraints.

---

## Part 2: Reading Stock Ranking Outputs

When you run `score-latest`, you get a CSV with the top-ranked stocks and their feature breakdowns. Here is how to interpret each column.

### 2.1 Core Ranking Columns

#### Score / Predicted Excess Return

**What it is:**
- The model's predicted alpha (excess return vs. benchmark) for that stock over the next 3 months.
- Produced by your LightGBM cross-sectional model based on features.
- Reported as a decimal (e.g., 0.0841 â‰ˆ 8.41% predicted excess return).

**How to read it:**
- **Higher score = model thinks it will outperform more** over the next 3 months.
- Scores are relative rankings, not absolute certainties.
- You should NOT trust the absolute magnitude; instead, use the ranking order.

**Example from your run:**

```
BA:   score=0.8103,  predicted_return=0.0841  (8.41%)
VST:  score=0.7648,  predicted_return=0.0922  (9.22%)
NKE:  score=0.7619,  predicted_return=0.0809  (8.09%)
AMD:  score=0.7560,  predicted_return=0.2243  (22.43%)  â† Outlier!
UNH:  score=0.7534,  predicted_return=0.0169  (1.69%)
```

**Observations:**
- BA, VST, NKE, UNH have similar overall scores (0.76â€“0.81), so they are "peers."
- But predicted returns vary widely: VST â‰ˆ 9%, UNH â‰ˆ 1.7%.
- AMD's 22.43% is a huge outlier; inspect AMD's features (technical? fundamental? sentiment?) to understand why.
  - If it is because RSI is extremely low + valuation is cheap, that is reasonable.
  - If it is because sentiment jumped overnight, be cautious (could be noise).

**When to be skeptical:**
- If one or two names have predicted returns 5Ã— the others, inspect them in detail.
- If the outlier is a volatile, low-volume name, it may be overfitting or curve-fitting.

#### Rank / Percentile

**What it is:**
- The rank order (1 = best, 2 = second-best, etc.) and percentile within the universe.
- Useful for filtering: "I only want the top 10 or top decile."

**How to use it:**
- You may rebalance into the top N names (e.g., top 10 or top 20).
- Or a top-decile approach: if universe is 500 stocks, buy the top 50.
- Higher rank = more conviction from the model.

**Example:**
- You bought ranks 1â€“10 (top 10 names).
- Those were: BA, VST, NKE, AMD, UNH, URA, NLR, CEG, HD, PG.
- This gave you a "balanced" portfolio because they span sectors (blue chips, nuclear, tech, healthcare).

---

### 2.2 Component Scores

#### Tech Score

**What it is:**
- Model's assessment of the **technical / momentum strength** for this stock.
- Ranges 0â€“1, where 1 = strongest technicals (recent momentum, RSI patterns, etc.).

**How to read it:**
- High tech score (0.90+): strong uptrend, good technicals, positive momentum.
- Medium tech score (0.50â€“0.80): mixed signals, not strongly trending.
- Low tech score (<0.50): weak momentum, downtrend, or overbought/oversold extremes.

**Example from your run:**

```
BA:   tech_score=0.9722  â† Very strong technicals
VST:  tech_score=0.9630
NKE:  tech_score=0.9537
AMD:  tech_score=0.9537
UNH:  tech_score=0.8148  â† Weakest technical here
```

**Interpretation:**
- BA, VST, NKE, AMD all have very strong technical setups (all > 0.95).
- UNH is weaker on technicals (0.81) but still ranked 5th overall; this means fundamentals + sentiment must be very strong.
- This shows your model is **not** pure momentum; it balances across factors.

**When tech score matters:**
- For very short-term (days/weeks), high tech score is critical.
- For mid-term (3 months), technical is one input; don't over-weight it.
- Example: "VST has weak technicals (0.50) but strong fundamentals â†’ might be a contrarian buy as technicals improve; monitor for entry."

#### Fundamental Score

**What it is:**
- Model's assessment of **valuation, earnings, quality, and balance-sheet strength**.
- Ranges 0â€“1, where 1 = best fundamentals (cheap, growing, healthy balance sheet).

**How to read it:**
- High fund score (0.75+): value or growth; earnings growth is present or valuation is cheap.
- Medium fund score (0.50â€“0.75): neutral; not a screaming bargain, not overpriced.
- Low fund score (<0.50): expensive relative to earnings, weak growth, or balance-sheet concerns.

**Example from your run:**

```
BA:   fund_score=0.7665  â† Good fundamentals
VST:  fund_score=0.6056
NKE:  fund_score=0.6478
UNH:  fund_score=0.7284  â† Strong despite weak technicals
PG:   fund_score=0.7369  â† Rank 10, buoyed by fundamentals
```

**Interpretation:**
- BA and UNH have strong fundamentals; UNH is ranked 5 despite weak technicals because of solid fundamentals + positive sentiment.
- VST ranks 2 but has only moderate fundamentals (0.61); it is being driven up by strong technicals + positive sentiment.
- This suggests your model is diversifying across factor styles: momentum plays (VST), value plays (BA), and quality plays (UNH).

**When fundamental score matters:**
- For mid-term (3â€“12 months), fundamentals are more durable than technicals.
- Strong fundamental score with weak technicals â†’ potential contrarian opportunity as technicals catch up.
- Weak fundamental score with strong technicals â†’ momentum play; more risky; watch for reversal.

#### Sentiment Score

**What it is:**
- Aggregate sentiment from recent news, social media, or analyst chatter about this stock.
- Ranges 0â€“1, where 1 = most positive sentiment.
- Usually computed as average or weighted-average of recent articles/posts.

**How to read it:**
- High sentiment (0.60+): recent news is positive; "the market likes this."
- Medium sentiment (0.40â€“0.60): neutral; mixed bag of good and bad news.
- Low sentiment (<0.40): negative; bad press, downgrades, or concerns.

**Example from your run:**

```
All names:          sentiment roughly 0.47â€“0.64 (tight cluster)

UNH:  sent_score=0.6375  â† Highest sentiment
AMD:  sent_score=0.5372
BA:   sent_score=0.4712  â† Lowest sentiment
```

**Interpretation:**
- Your entire top-20 list has sentiment in a narrow band (0.47â€“0.64), centered around 0.55 (neutral-to-slightly-positive).
- This is **healthy for a diversified portfolio**: you are not picking stocks that are sentiment-hyped or severely despised.
- UNH's highest sentiment (0.64) is still only slightly positive; it is not a "darling" that risks sudden reversal.
- BA's lowest sentiment (0.47) means there is some negative news (Boeing safety issues, supply-chain concerns), but not overwhelming.

**When sentiment matters:**
- Sentiment is **confirmatory**, not primary for mid-term.
- Use it to:
  - Confirm a high-scoring name (good tech + good fund + positive sentiment = strong conviction).
  - Warn about a conflicted name (good fundamentals + negative sentiment = something is up; investigate before buying).
  - Avoid consensus bubbles (if every name has 0.90+ sentiment, you're at peak greed; reduce size).

**Diagnostics:**
- Is sentiment aligned with technicals and fundamentals, or do they diverge?
  - Aligned â†’ model is coherent.
  - Diverged â†’ opportunity (if sentiment is lagging) or risk (if fundamentals are lagging).

---

### 2.3 Feature Columns

#### RSI (Relative Strength Index)

**What it is:**
- Momentum oscillator on a scale 0â€“100 measuring the speed/magnitude of recent price moves.
- Formula uses 14-day period typically: RSI = 100 âˆ’ (100 / (1 + RS)), where RS = avg gain / avg loss.

**How to read it:**
- RSI > 70: overbought; stock has risen sharply; risk of pullback or consolidation.
- RSI 40â€“60: neutral; no strong momentum signal.
- RSI < 30: oversold; stock has fallen sharply; potential bounce or reversal.

**Example from your run:**

```
BA:   RSI=85.37  â† Very overbought
VST:  RSI=47.91  â† Neutral
NKE:  RSI=44.53  â† Neutral
AMD:  RSI=42.97  â† Neutral
MU:   RSI=66.18  â† High but not extreme
```

**Interpretation:**
- BA is very overbought (RSI 85); it has risen a lot recently. **Risk**: pullback or consolidation could hurt short-term returns.
  - For a 3-month hold, overbought isn't a deal-breaker, but size smaller if nervous.
- Most others are in neutral zone, which is good for mid-term; they have room to run without being overextended.
- MU at 66 is elevated but healthy; not extreme.

**Caution:**
- Overbought can stay overbought for a long time; don't panic-sell.
- Oversold can bounce, but doesn't guarantee upside; use with other signals.

#### Return 21d, Return 63d (1-month and 3-month past returns)

**What it is:**
- Realized return over the past 21 days (â‰ˆ1 month) and 63 days (â‰ˆ3 months).
- Positive = stock has gone up; negative = stock has gone down.

**How to read it:**
- Strong positive return recently (e.g., +15% in 21d) = momentum is up; good technical setup.
- Weak or negative return (e.g., â€“5% in 21d) = potential reversal point or weakness.
- Multi-period check: if 21d is weak but 63d is strong, momentum may be stalling; if both are strong, momentum is robust.

**Example from your run:**

```
BA:   return_21d=+15.61%   (strong recent momentum)
VST:  return_21d=âˆ’8.95%    (weak; declining)
NKE:  return_21d=âˆ’4.72%    (weak)
AMD:  return_21d=âˆ’0.10%    (flat; no recent move)
MU:   return_21d=+23.79%   (very strong)
```

**Interpretation:**
- BA and MU have strong recent momentum; good for short-term/technical perspective.
- VST, NKE, AMD have weak or negative recent performance; they are "falling knives" or consolidating.
- **Mid-term view**: weak recent performance + good fundamentals = contrarian setup; they may recover over 3 months.
  - Example: VST is rank 2 overall with good fundamentals, but down 8.95% in past month; could be a value + reversal play.

#### Volatility (Rolling Std Dev)

**What it is:**
- Annualized rolling standard deviation of daily returns (usually 20â€“60 day window).
- Measures how much the stock bounces around; higher = choppier.

**How to read it:**
- High volatility (0.40+): risky; stock swings a lot; good for traders, bad for risk-averse investors.
- Medium volatility (0.20â€“0.40): typical equity volatility; reasonable for most strategies.
- Low volatility (< 0.20): stable; blue-chip or utility stocks; lower risk.

**Example from your run:**

```
BA:   volatility=0.3988  â† Above-average but not extreme
VST:  volatility=0.4612  â† High; nuclear theme is risky
URA:  volatility=0.4979  â† Very high; uranium miner; volatile commodity play
MU:   volatility=0.6319  â† Extremely high; semiconductor cyclical
HD:   volatility=0.1869  â† Low; Home Depot is stable
UNH:  volatility=0.2600  â† Low; healthcare is defensive
```

**Interpretation:**
- Your portfolio is a **mix of high-vol and low-vol names**:
  - Nucle plays (VST, URA), semiconductors (MU, INTC), and cyclicals (BA) = high volatility.
  - Utilities (DUK, NEE, SO), healthcare (UNH), and staples (PG, COST) = low volatility.
- If equal-weighted, the high-vol names dominate portfolio risk, dragging down Sharpe.
- **Action**: reweight by inverse volatility or set fixed % allocation to each sector to control total risk.

#### Sector

**What it is:**
- Industry classification (Blue Chip, Tech, Nuclear, Healthcare, Utilities, etc.).

**How to use it:**
- Check for over-concentration: "Do I have too much nuclear (5 of 20)?"
- Use sector to apply position caps (e.g., "Max 25% in any sector").
- Check sector performance: if Tech underperforms, does your strategy suffer?

**Example from your run:**
```
Nuclear:        4 names (VST, URA, NLR, CEG, CCJ)  â†’ 20% of top 20
Tech/Semis:     4 names (AMD, META, INTC, MU)     â†’ 20% of top 20
Utilities:      3 names (SO, NEE, DUK)            â†’ 15% of top 20
Consumer:       3 names (NKE, HD, COST)           â†’ 15% of top 20
Blue Chips:     4 names (BA, CAT, PG, + 1 overlap?) â†’ ~20% of top 20
Healthcare:     1 name (UNH)                       â†’ 5% of top 20
```

**Observation:**
- Fairly balanced! No sector exceeds 20%; this matches your "balanced portfolio across sectors" tag.
- Nuclear is over-represented at 20%; if your max sector cap is 15%, you'd trim one nuclear name.
- This suggests your model is picking from across factors/styles, not just chasing one trend (good).

---

## Part 3: Diagnostic Checklist for Your Backtests

Use this checklist after each backtest run to quickly spot issues.

### 3.1 Return & Risk Alignment

- [ ] **Sharpe ratio > 0.5?** If below 0.5, returns don't justify the volatility; improve model or reduce position count.
- [ ] **Max drawdown acceptable to you?** If past your pain tolerance, the strategy fails even if it's profitable.
- [ ] **Return > 2x the benchmark?** If benchmark (S&P 500) did 10% and you did 12%, you're barely adding value.
- [ ] **Win rate > 55%?** Below 55%, you're not consistently beating the benchmark; reconsider.

### 3.2 Data Quality & Leakage

- [ ] **No survivorship bias?** If testing on "current S&P 500," adjust for historical membership.
- [ ] **Fundamentals are lagged?** Earnings data should not be usable until ~1 week after report date.
- [ ] **Sentiment data time-aligned?** News should only be counted if published before the decision time.
- [ ] **Look-ahead in features?** Forward-fill is OK; forward-filling from future data is not.

### 3.3 Cost & Slippage Realism

- [ ] **Costs included?** Commission (per trade), bidâ€“ask spread (~5â€“10 bps for liquid large-caps), slippage.
- [ ] **Position sizes realistic?** Don't trade 50% of portfolio in illiquid names in one day.
- [ ] **Turnover reasonable?** If above 30% monthly, costs will drag returns; may need to reduce rebalance frequency.

### 3.4 Feature & Model Sanity

- [ ] **Outlier predictions?** If one stock has predicted return 5Ã— the median, investigate (overfitting?).
- [ ] **Tech, fundamental, sentiment scores balanced?** If all names have similar scores, model may not be discriminating.
- [ ] **Sector concentration?** No sector > 25% (or your cap); avoid concentration risk.
- [ ] **Feature correlations checked?** High correlation between features can cause instability.

### 3.5 Robustness Across Time & Regime

- [ ] **Performance stable across years?** Win in 2022, lose in 2023? Strategy is regime-dependent.
- [ ] **Works in bull AND bear markets?** Test on 2008, 2020, 2022 downturns to see how it handles stress.
- [ ] **Low volatility regime (2017) vs. high volatility (2018, 2022)?** Adjust leverage or position sizing if needed.

### 3.6 Out-of-Sample Validation

- [ ] **Train/test split used?** Never evaluate on data used for training; use walk-forward or time-series split.
- [ ] **Test set performance similar to train?** If test Sharpe is half of train, overfitting is likely.
- [ ] **Hyperparameters tuned only on training window?** If you tuned on full data, that's curve-fitting.

---

## Part 4: Example Interpretation Workflow

Here is a step-by-step workflow for analyzing your backtest runs:

### Step 1: Glance at Summary Metrics

```
Return:   +12.00%
Sharpe:   0.11
Win Rate: 56.63%
```

â†’ **Verdict**: Modest profitable, but low Sharpe and barely-above-50% win rate suggest weak edge.

### Step 2: Check Risk Metrics (not in summary; check full report)

```
Max Drawdown:  (check your output)
Turnover:      (check your output)
```

â†’ If max DD > 25% and turnover > 30%, the strategy is risky and costly; needs improvement.

### Step 3: Examine Top Holdings

Open the CSV ranking output:

```
Rank 1:  BA   (score=0.81, tech=0.97, fund=0.77, sent=0.47)  â†’ Strong on tech & fund, weak on sentiment
Rank 2:  VST  (score=0.76, tech=0.96, fund=0.61, sent=0.51)  â†’ Momentum play; weak fundamentals
Rank 3:  NKE  (score=0.76, tech=0.95, fund=0.65, sent=0.45)  â†’ Balanced, but negative recent sentiment
Rank 4:  AMD  (score=0.76, predicted=0.22)                   â†’ Outlier! Investigate why.
```

â†’ **Diagnosis**:
- AMD's outsized prediction (22% vs. others ~8%) drives much of the expected alpha.
- If AMD is overweighting the portfolio, total portfolio performance is betting on one name.
- Check AMD's features (is it oversold, cheap, or just recent momentum?).

### Step 4: Feature-Level Diagnostics

- Check RSI: Are top picks overbought (RSI > 70)? If yes, expect pullback risk.
- Check volatility: Are top 5 picks high-vol (0.40+)? If yes, reweight by inverse volatility.
- Check sectors: Any sector > 25% of portfolio? If yes, reduce concentration.

### Step 5: Time-Series Diagnostics

- Plot equity curve over time; does it look like a smooth uptrend or a jagged, recovery-prone drawdown?
- Do returns cluster in certain years? (E.g., all gains in 2023, all losses in 2024?)
- If clustering, strategy may not be robust; test specifically in bear markets.

### Step 6: Decide: Accept, Improve, or Reject

| Metric | Good | Action |
|---|---|---|
| Sharpe > 1.0, Win > 60%, Return > 2x benchmark, Smooth equity curve | âœ… | Consider live trading or expand to more names. |
| Sharpe 0.5â€“1.0, Win 55â€“60%, Return > 1.2x benchmark, Mild drawdowns | âš ï¸ | Improve: reduce costs, reweight by volatility, refine features. |
| Sharpe < 0.5, Win < 55%, Return < 1.1x benchmark, High drawdowns | âŒ | Reject or redesign. Debug overfitting, data leakage, or model feature engineering. |

---

## Part 5: Common Red Flags & Fixes

### Red Flag 1: "Sharpe is good in backtest but low in real trading"

**Likely cause**: Overfitting, data leakage, or unrealistic costs.

**Fix**:
- Run walk-forward backtest (retrain model each month; don't reuse old weights).
- Increase position count and reduce allocation per position (less concentration risk).
- Add realistic slippage (2â€“5 bps per trade) and lower expected returns accordingly.

### Red Flag 2: "Win rate is above 55% but Sharpe is still low"

**Likely cause**: Win sizes are small, loss sizes are large. You're right often but pay big when wrong.

**Fix**:
- Check the average win vs. average loss ratio.
- Use stop-losses to cap downside on losing positions.
- Improve model to avoid large consensus-bet failures.

### Red Flag 3: "One or two stocks dominate predicted returns"

**Likely cause**: Outlier features or model overfitting to recent data.

**Fix**:
- Inspect the outliers' features; are they rationally justified?
- Cap predicted returns to Â±2 standard deviations to reduce outliers.
- Reweight portfolio by conviction (score) to avoid betting too much on marginal bets.

### Red Flag 4: "Portfolio volatility is 3x higher than benchmark"

**Likely cause**: High-beta stock selection, concentrated bets, or equal-weighting high-vol names.

**Fix**:
- Reweight by inverse volatility (smaller bets on risky names).
- Add a volatility constraint: target portfolio volatility = benchmark volatility (or slightly higher).
- Diversify across more names; reduce per-position size.

### Red Flag 5: "Max drawdown is 40%+ but backtest shows +15% return"

**Likely cause**: Lucky recovery during backtest period; strategy may not be robust.

**Fix**:
- Test on multiple historical periods; what was max DD in 2008 or 2020?
- Implement a portfolio-level stop-loss or volatility circuit breaker.
- Consider risk-parity sizing (equal risk, not equal dollar, per position).

---

## Part 6: Quick Reference: Metrics Cheat Sheet

| Metric | Formula / Definition | Good Value | Red Flag |
|---|---|---|---|
| **Return (annual)** | Total gain / Starting capital, annualized | > 10% | < 5% or < 1.2Ã— benchmark |
| **Sharpe Ratio** | (Return âˆ’ Risk-Free) / Volatility | > 1.0 | < 0.5 |
| **Sortino Ratio** | (Return âˆ’ Risk-Free) / Downside Volatility | > 1.5 | < 0.8 |
| **Max Drawdown** | Peak-to-trough decline | âˆ’10% to âˆ’20% | < âˆ’40% |
| **Win Rate** | % of periods beating benchmark | > 60% | < 55% |
| **Turnover (monthly)** | Average portfolio rebalance size | 10â€“30% | > 50% |
| **Hit Rate (per trade)** | % of individual trades that profit | > 55% | < 50% |
| **Payoff Ratio** | Avg win size / Avg loss size | > 1.5 | < 1.0 |
| **Profit Factor** | Gross wins / Gross losses | > 1.5 | < 1.2 |
| **Calmar Ratio** | Return / Max Drawdown (absolute) | > 1.0 | < 0.5 |

---

## Part 7: Putting It All Together for Your Strategy

Given your mid-term (3-month) horizon, "balanced" portfolio, and focus on interpretability, here is your personal target metrics dashboard:

**MVP (Minimum Viable Strategy)**:
- Sharpe: â‰¥ 0.8 (not just 0.11).
- Win rate: â‰¥ 58% (not 56.63%).
- Max drawdown: â‰¤ â€“20% (acceptable pain).
- Turnover: 15â€“25% monthly (manageable costs).
- Sector concentration: No sector > 20% (true diversification).

**Improvements to chase**:
1. Reweight portfolio by inverse volatility (avoid equal-weight of disparate risk names).
2. Improve sentiment feature integration; currently it's a weak tilter.
3. Add regime filter: "Don't trade in high-volatility periods unless predicted returns are > 3x."
4. Run A/B tests: "With sentiment" vs. "Without sentiment" to verify it adds value.
5. Validate on out-of-sample test set (e.g., last 6 months of data not used in training).

With these refinements, you can realistically target:
- Sharpe: 1.0â€“1.5.
- Win rate: 58â€“65%.
- Max DD: â€“15% to â€“25%.
- Return: 12â€“18% annualized.

This would be a **strong, tradable strategy** for a mid-term, stewardship-oriented investor.

---

**End of Guide**

Use this as a reference whenever you run a new backtest. Highlight sections relevant to your current workflow and refine the checklist as you build more features.