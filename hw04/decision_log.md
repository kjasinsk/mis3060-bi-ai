# HW4 Decision Log — Wildcat Capital data cleaning

**Author:** Kaitlyn Jasinski · **Course:** MIS3060 · **Written:** before `02_clean.py` was generated

This log is the prompt I gave Claude Desktop for the cleaning script. Every number comes from `reports/dq_summary_raw.csv`, produced by `scripts/01_profile.py` on the raw files. Issues I decided **not** to fix are logged too (entries 9–21), because deciding to leave something alone is still a decision.

**Rule I followed:** fix a value only when another column or another table proves what the right value is. If nothing proves it, I **flag** it (add a 0/1 column) or **quarantine** it (move the row to a separate file). I never invent a value.

---

## Order of operations (and why)

1. **Quarantine first** (duplicate clients, then orphan transactions). There is no point repairing rows I'm about to remove, and removing them first keeps the "rows affected" counts honest.
2. **Repair values next**, one column at a time, each one checked against a second source (another column or another table).
3. **Format changes** (same value, different spelling) after the repairs.
4. **Flags last**, so they are computed on the final, cleaned values.

---

## Issues I fixed

### 1. Duplicate clients with a misspelled last name
| Field | |
|---|---|
| **Table / column** | `dim_client` / `client_id` (business key: first_name, zip_code, age, client_since, initial_aum) |
| **Evidence** | 25 rows (IDs 2501–2525) match an existing client on **every** column except `client_id` and `last_name`, and the last name is a one-letter typo of the real one: 23 drop the last letter, 2 add a letter (2512 "Leen" for 1193 "Lee", 2515 "Pacen" for 889 "Pace"). Example: 2501 "Taylo" copies 674 "Taylor"; 2503 "Jacobso" copies 99 "Jacobson". **0** fee, snapshot or transaction rows use IDs 2501–2525. |
| **Dimension violated** | Uniqueness |
| **Decision** | **Quarantine** the 25 rows to `data/audit/quarantine_dim_client_duplicates.csv`, keeping a column that names the original client ID. |
| **Justification** | Each one is the same person entered twice. Keeping them would count 25 extra clients in any headcount or AUM-by-client report. They have no activity, so nothing is lost by removing them. |
| **Risk** | If any of them were really a second account for the same person, we would undercount accounts by 25. That is low risk: with no fees, snapshots or trades, they hold no money we can see. |

### 2. Transactions for clients who do not exist
| Field | |
|---|---|
| **Table / column** | `fact_transactions` / `client_id` → `dim_client.client_id` |
| **Evidence** | 200 rows (txn_id 298,573–298,772, the last 200 rows of the file) use client IDs 2702–3192. The client table stops at 2525. Each orphan row has a **different** client ID, and no other table has heard of them. Match rate 99.933%. |
| **Dimension violated** | Referential Integrity |
| **Decision** | **Quarantine** to `data/audit/quarantine_fact_transactions_orphans.csv`. |
| **Justification** | A transaction with no client can't be put on any client, advisor or region report, and an inner join in Power BI would drop it silently anyway. Better to drop it on purpose with a paper trail. There is no way to tell which real client they belong to: each advisor ID is shared by 81–118 clients. |
| **Risk** | If these are real clients missing from the client file, we understate activity by 200 trades (0.07% of rows). The quarantine file keeps every column, so they can be put back once the missing clients arrive. |

### 3. State written as a full name
| Field | |
|---|---|
| **Table / column** | `dim_client` / `state` |
| **Evidence** | 78 of 2,525 rows use full names (Pennsylvania 25, Florida 15, New York 14, New Jersey 13, California 5, Illinois 4, Texas 2). The other 2,447 use 2-letter codes. One "Florida" row is a duplicate client (#1), so **77** are fixed after quarantine. |
| **Dimension violated** | Consistency, Validity |
| **Decision** | **Standardize** to the USPS 2-letter code (Pennsylvania → PA). |
| **Justification** | A map or a "clients by state" chart would otherwise show Pennsylvania and PA as two different states, which would split 25 clients away from PA. |
| **Verification** | Every full name maps to exactly one code. After the fix, every state must be in the list of valid codes (`assert`). |
| **Risk** | Basically none. The mapping is one-to-one, and the original text is saved in `value_changes.csv`. |

### 4. Blank risk profile
| Field | |
|---|---|
| **Table / column** | `dim_client` / `risk_profile` |
| **Evidence** | 76 blanks. One belongs to a duplicate client (#1), so 75 remain. In the snapshot table, each risk profile always uses the same benchmark (true for 100% of the 2,425 clients with a known profile), and benchmark 3 (60/40 Blend) is used **only** by "Balanced" clients. All 75 blank-profile clients use benchmark 3. |
| **Dimension violated** | Completeness |
| **Decision** | **Fill** with "Balanced" **and flag** it with a new column `risk_profile_inferred = 1`. |
| **Justification** | Suitability and performance reports group clients by risk profile. 75 clients in a "(blank)" bucket hides 3% of the book. The benchmark proves the answer, so this is a repair, not a guess, and the flag keeps it honest. |
| **Risk** | If the benchmark was given out by default when the profile was missing, these clients may not really be "Balanced". The flag column lets compliance find all 75 and confirm them with the advisor. |

### 5. Buy transactions with negative shares
| Field | |
|---|---|
| **Table / column** | `fact_transactions` / `shares` (sign rule: shares are always positive; direction comes from `txn_type`) |
| **Evidence** | 836 rows, all `Buy` (835 after the orphans are removed). For 100% of them, `|shares| × price = amount` to the cent. The amount is positive, as it is for every other buy. |
| **Dimension violated** | Validity, Accuracy |
| **Decision** | **Convert**: remove the minus sign. |
| **Justification** | A negative buy would subtract shares from a holding that should grow, so position and cost-basis totals would be wrong. The amount column proves the magnitude was right and only the sign was wrong. |
| **Verification** | After the fix, `shares × price = amount` for all of these rows, and no negative shares remain (`assert`). |
| **Risk** | If some were really sells keyed as buys, flipping the sign keeps them as buys. But `txn_type` and the positive amount both say "Buy", so two columns agree against one. |

### 6. Returns stored as percent text ("9.28%")
| Field | |
|---|---|
| **Table / column** | `fact_portfolio_snapshot` / `return_ytd` |
| **Evidence** | 300 rows are written like `9.28%`, while the other 129,247 are decimals like `0.0928`. Pandas can't read the percent ones as numbers. After dividing by 100, **300 of 300** equal `benchmark_return_ytd + active_alpha_ytd` within half a basis point (0.00005). The small gap is only because these were rounded to 2 decimals. |
| **Dimension violated** | Validity, Consistency |
| **Decision** | **Convert**: strip the `%` and divide by 100. |
| **Justification** | In a BI tool, either the whole column would load as text, so no averages are possible, or these rows would load as blank. Either way, average return would be wrong. |
| **Verification** | Recompute benchmark + alpha and compare (`assert` every converted row is within 0.00005). |
| **Risk** | Low: the reconciliation proves the meaning. Limitation: these 300 values keep only 4 decimal places of precision. I did **not** overwrite them with benchmark + alpha, because that would replace a recorded value with a calculated one. |

### 7. Security ID stored as "45.0"
| Field | |
|---|---|
| **Table / column** | `fact_transactions` / `security_id` |
| **Evidence** | All 197,175 non-blank values look like `45.0`, while `dim_security.security_id` looks like `45`. As text they don't match: `check_referential_integrity` gives a **0%** match on the raw file, and only **33.98%** of raw transactions join to every dimension. By value, 100% would match, so this is a format defect, not missing securities. This is exactly what default `read_csv` hides. 197,044 rows remain after the orphan quarantine. |
| **Dimension violated** | Validity, Consistency (and Referential Integrity once it's loaded as text) |
| **Decision** | **Convert** to whole-number text (`45.0` → `45`). Blanks stay blank. |
| **Justification** | Needed so the column can be a whole-number key that joins to `dim_security`. |
| **Verification** | Every value must end in `.0` before the fix (no real decimals lost), and 100% must match `dim_security` after it (`assert`). |
| **Risk** | None if every value ended in `.0`, which the `assert` checks. |

### 8. Numbers written in scientific notation
| Field | |
|---|---|
| **Table / column** | `fact_portfolio_snapshot` / `return_ytd` (135 rows), `active_alpha_ytd` (756 rows) |
| **Evidence** | Values like `9.9e-05`. These are correct numbers, just tiny ones written differently. |
| **Dimension violated** | Consistency |
| **Decision** | **Standardize** to plain decimals (`9.9e-05` → `0.000099`), with no change in value. |
| **Justification** | Some tools and Excel imports treat these as text. One format per column is safer for Assignment 5. |
| **Verification** | `assert` that the number before and after is exactly equal. |
| **Risk** | None. The value is identical. |

---

## Issues I flagged but did NOT change (suspicious, can't be proven wrong)

### 9. Buys and sells on weekends
| Field | |
|---|---|
| **Table / column** | `fact_transactions` / `txn_date` vs `dim_date.is_trading_day` |
| **Evidence** | 40,649 Buy/Sell rows (40,630 after quarantine) are dated Saturday or Sunday, when markets are closed. That's 28.4% of trades, almost exactly the weekend share of the calendar (28.6%), so dates look randomly assigned. |
| **Dimension violated** | Accuracy/Plausibility |
| **Decision** | **Flag**: new column `flag_non_trading_day = 1`. |
| **Justification** | A trade can't fill on a Saturday. Most likely this is the date the order was entered, not when it filled. But nothing tells me the real fill date, so moving it to Monday would be inventing data. |
| **Risk** | If someone uses these dates to price trades against daily market data, there's no price that day. The flag lets them filter or roll the date forward on purpose. |

### 10. Activity after a client left
| Field | |
|---|---|
| **Table / column** | `fact_transactions` / `txn_date` vs `dim_client.is_active` + last snapshot month |
| **Evidence** | 2,410 transactions for 131 of the 175 inactive clients are dated after their last month on the books. |
| **Dimension violated** | Accuracy/Plausibility, Consistency |
| **Decision** | **Flag**: `flag_after_client_exit = 1`. |
| **Justification** | Could be closing trades and transfers out (legitimate), or bad dates. Deleting them would hide money movement, so I'm keeping them visible. |
| **Risk** | Activity reports for "current clients" may include these unless they're filtered on the flag. |

### 11. Year-to-date return above 100%
| Field | |
|---|---|
| **Table / column** | `fact_portfolio_snapshot` / `return_ytd` |
| **Evidence** | 977 rows (144 clients) have a return above +100% or below −100% (max 94.67, i.e. +9,467%). They **do** equal benchmark + alpha, and they follow jumps in AUM, so the "return" includes deposits and withdrawals, not just investment growth. |
| **Dimension violated** | Accuracy/Plausibility |
| **Decision** | **Flag**: `flag_extreme_return = 1`. |
| **Justification** | Not a typo: the row is internally consistent. But it isn't a true investment return, and one +9,467% row would wreck an average-return measure. |
| **Risk** | Averages that include these rows will be badly skewed. The README tells Power BI users to exclude flagged rows or use a median. |

### 12. AUM stuck at exactly $1,000
| Field | |
|---|---|
| **Table / column** | `fact_portfolio_snapshot` / `aum` |
| **Evidence** | 420 rows are exactly 1000.0, the minimum value in the column, often for several months in a row. This looks like a floor the source system applies when an account is drained. |
| **Dimension violated** | Accuracy/Plausibility |
| **Decision** | **Flag**: `flag_aum_floor = 1`. |
| **Justification** | The true value is probably near zero, but I can't prove what it was. $1,000 × 420 rows is $420K, against a book of about $12.7B at Dec-2024, so it's immaterial to totals. It matters for per-client returns, though. |
| **Risk** | Small overstatement of AUM for drained accounts. |

---

## Things that look odd but are correct (legitimate structure — left as is)

| # | Table / column | Evidence | Dimension | Decision | Why it is not a defect | Risk |
|---|---|---|---|---|---|---|
| 13 | `dim_security.sector`, `expense_ratio_bps` | 219 blank sectors = exactly the 219 ETFs; 281 blank expense ratios = exactly the 281 non-ETFs | Completeness | **Leave as is** | An ETF holds many sectors, and a single stock has no expense ratio. Filling either would invent data. The validator checks the pattern is exact. | If some blanks were real missing data, sector or expense reports would leave out those securities. Low: the blanks line up exactly with `is_etf`. |
| 14 | `fact_transactions.security_id`, `shares`, `price` | 101,597 blanks = exactly the Deposit, Withdrawal and Advisory Fee rows | Completeness | **Leave as is** | Cash moving in or out involves no security. | If a cash-flow row was supposed to carry a security, holdings would be understated. Low: the blanks match the transaction types exactly. |
| 15 | `dim_advisor.certifications` | 6 advisors have the text `None` | Validity | **Leave as is** | It means "no certification", a real answer. Default `read_csv` would have turned it into a missing value. I documented this so Power BI users don't treat it as blank. | If a BI tool reads `None` as blank, those 6 advisors look like missing data instead of "no certification". |
| 16 | `dim_client.zip_code` | 232 ZIPs start with 0 (e.g. 02068) | Validity | **Leave as text** | Reading them as numbers would drop the zero. README tells the BI tool to load ZIP as text. | If ZIP is loaded as a number, 232 ZIPs lose their leading zero and won't map to the right location. |
| 17 | `fact_portfolio_snapshot` | 7,350 client-months have a snapshot but no fee row | Completeness | **Leave as is** | Spread across all months and clients, consistent with fee waivers. Nothing in the data says what the fee should have been. | If these are missed fees rather than waivers, fee revenue is understated for those 7,350 client-months. |
| 18 | `dim_benchmark` | Benchmark 6 (MSCI Emerging Markets) is used by no client or security | Referential Integrity | **Leave as is** | A dimension may list members that aren't used yet. | Very low: it only shows up as an empty option in a benchmark filter. |
| 19 | Inactive clients | 175 inactive clients' snapshots stop between Dec-2022 and Nov-2023 | Consistency | **Leave as is** | That's what "inactive" means. Their history is still real. | If some inactive clients still hold money, their AUM is missing after the last snapshot. |

## Known limitations I am documenting but not fixing

| # | Table / column | Evidence | Dimension | Decision | Justification / Risk |
|---|---|---|---|---|---|
| 20 | `fact_transactions.amount` for `Dividend` | All 53,864 dividends equal shares × price, i.e. the **whole position value** (a 100% yield) | Accuracy/Plausibility | **Leave as is, document** | Real dividends are a few percent of value. Since it's every single dividend, this is how the source system defines the field, not a random error, and I can't recompute a true dividend. **Risk:** "income" totals are hugely overstated. Don't report dividend income from this column. |
| 21 | Advisory Fee transactions vs `fact_fees` | 1 of 28,746 client-months match to the cent (0.0035%, a coincidence), and totals differ (transaction debits = $263.7M vs fees table = $204.7M) | Consistency | **Leave as is, document** | Two systems disagree, and I can't tell which is right. **Decision for reporting:** use `fact_fees` as the source of fee revenue, because its `amount` reconciles 100% to `aum_basis × bps ÷ 12` and its `aum_basis` matches the snapshot AUM 100%. **Risk:** anyone adding both tables would double-count fees. |
