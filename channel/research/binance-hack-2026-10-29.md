# Binance hack, 2026-10-29: facts brief

Researched 2026-10-31. Story is days old and still moving. Every figure below is "as reported on the date shown", not verified by us. Several outlets (Al Jazeera, CNBC, Business Standard, Yahoo Finance) were read through a page summarizer, so exact wording should be re-checked before quoting. Direct fetches of TechCrunch, Forbes, Bloomberg and the original Al Jazeera economy URL failed (404/403); they are NOT used as sources.

## Sources read
- Al Jazeera, 2026-10-30: https://www.aljazeera.com/news/2026/10/30/binance-says-6-3bn-stolen-in-biggest-crypto-heist-in-history-what-we-know
- CoinDesk, 2026-10-30: https://www.coindesk.com/business/2026/10/30/binance-arranges-usd6-34-billion-to-cover-losses-from-record-crypto-hack
- CNBC, 2026-10-29: https://www.cnbc.com/2026/10/29/circle-tether-freeze-funds-impacted-by-potential-binance-security-issue.html
- Yahoo Finance (bitcoin drops to $76,000), 2026-10-30/31: https://finance.yahoo.com/markets/article/bitcoin-drops-to-76000-as-binance-hack-spooks-investors-tether-circle-freeze-assets-083406383.html
- Investing.com: https://www.investing.com/news/cryptocurrency-news/binance-halts-withdrawals-after-53-bln-hack-4985601
- MarketScale: https://www.marketscale.com/industries/software-and-technology/binance-pauses-withdrawals-after-a-theft-it-puts-at-6-3-billion-the-largest-crypto-hack-on-record
- Business Standard: https://www.business-standard.com/amp/world-news/binance-hit-by-record-6-3-bn-crypto-theft-north-korea-suspected-126103001944_1.html (search snippet only, page blocked)

## Confirmed (stated by Binance or multiple outlets)
| Fact | Detail | Source |
|---|---|---|
| Binance put the theft at about $6.3 billion | Binance's own estimate; "largest crypto theft on record" | Al Jazeera, CoinDesk, CNBC, Investing.com, MarketScale |
| Prior record | $1.5 billion, Bybit, February 2025 | Al Jazeera, Yahoo |
| Timing | Most of it over about 20 minutes, late Thursday 2026-10-29 (breach about 20:05 UTC; withdrawals paused about 22:15 UTC) | CoinDesk, Al Jazeera, MarketScale |
| Spread | Funds moved out of Binance wallets on 10 blockchains | Al Jazeera |
| Withdrawals paused | Deposits stayed open; Binance expects withdrawals back within 45-48 hours (about Sunday 2026-11-01) | CoinDesk, MarketScale, Yahoo (Yi He: "should resume within 48 hours") |
| Binance will cover losses | Co-CEO Richard Teng: committed to covering all hacked losses from company funds. Binance set aside about $6.34 billion; says it already holds about $5 billion of the affected tokens and is buying the rest | CoinDesk, Yahoo |
| Proof of Reserves | Binance spokesperson: "All user funds will be verified publicly through our Proof of Reserves." | CoinDesk |
| About $3 billion frozen | By stablecoin issuers and partners | Al Jazeera, CNBC, Yahoo, CoinDesk |
| Tether froze about $1.567 billion USDT | Yahoo says 1.567; CNBC says "1.5 billion" | Yahoo, MarketScale, CNBC |
| Circle froze about $800 million USDC | MarketScale says $823 million | CNBC, Yahoo, MarketScale |
| World Liberty Financial froze $27 million (USD1) | | Yahoo |
| Market reaction | Bitcoin fell to a six-week low ($76,368 per Al Jazeera; "below $77,000", -5% per Yahoo; -3.2% to $77,484 per Investing.com; "over 4%" to $77,187.60 per CNBC). Ether about $2,178-2,236. Coinbase shares fell about 4.8-5%. | Al Jazeera, Yahoo, CNBC, Investing.com |

Use "Bitcoin fell to around $76,000-$77,000, a six-week low" if mentioned at all; the percentage differs by outlet and time of day. The video does not mention price.

## Alleged / suspected (say "investigators point to", never state as fact)
- North Korea: TRM Labs ("high confidence") and Chainalysis say it looks like TraderTraitor, a North Korea-linked unit tied to Lazarus Group. Elliptic is also reported to agree (MarketScale). Binance's Teng: "Our investigation has not attributed responsibility to any individual." Governments have not formally confirmed (MarketScale). Sources: Al Jazeera, CoinDesk, CNBC, MarketScale.
- Cause: Binance initially pointed to a compromised DevOps/engineer laptop (CNBC). Teng later said the attack was "more complex" and found "additional points of breach" (Al Jazeera, CNBC). Binance says no evidence private keys leaked (Al Jazeera, MarketScale). Say: "initial investigation suggested a compromised engineer laptop; Binance now calls it a complex attack."
- CFTC Chairman Michael Selig called these "unregulated offshore exchanges" (CNBC, via summarizer). Opinion; not used.

## Conflicts between sources
- Amount stolen: Binance $6.3B; TRM Labs $6.36B; Elliptic $6.43B; Chainalysis about $5.9B (all MarketScale). Use "Binance says about $6.3 billion".
- Frozen: "about $3 billion" (Al Jazeera, CNBC, CoinDesk); Elliptic $2.84B (44%, MarketScale); Al Jazeera also says $2.3B by Tether and Circle alone. A "$2.54B frozen" figure was NOT found in any source read. Use "about $3 billion frozen, per reports" or avoid.
- Hack date: Al Jazeera's summary says Thursday "October 30"; Thursday was 2026-10-29 (MarketScale says Binance announced on "Friday, Oct 29", also inconsistent; Oct 29 was a Thursday). Use "late Thursday" only.
- Tether freeze 1.5B vs 1.567B; Circle 800M vs 823M. Use "about".
- Where the money sits: Elliptic/MarketScale say about $3.3B is outside reach including about 18,270 BTC across 19 addresses; one outlet lists stolen composition ($1.66B USDT, $1.45B BTC, $767M USDC). Single source; not used.

## Still unknown
- Final stolen total and final frozen total ("may continue to increase" per Al Jazeera).
- How the attacker got in (laptop only, or more points of breach).
- Whether and when stolen bitcoin is recovered.
- Whether withdrawals actually resume on schedule; the result of the Proof of Reserves check.
- Who did it. Attribution is analytics-firm assessment, not a formal finding.

## Lessons for ordinary savers (education, not advice)
1. Custody: coins on an exchange are an IOU from the exchange; the exchange holds the keys. Self-custody means you hold the keys, with its own risks (lost keys, scams). Neither is "safe"; each moves the risk somewhere else. No recommendation.
2. Why withdrawals get paused: platforms stop outflows to stop an attacker moving more, to revoke compromised addresses, and to check balances before reopening.
3. Proof of reserves: a public check that an exchange holds at least as many assets as customers are owed. It shows a snapshot of assets, not that the company is sound.
4. Where money sits: money spread across several places cannot all be stuck in one place on one bad night. Spreading where money sits is not a return promise.
5. Cover pledge: "we will cover losses" is a promise from the company; it is worth what the company can pay. Binance says it has set aside $6.34B.
Never: buy/sell/hold calls, price predictions, "guaranteed", income promises, accusations beyond sources.
