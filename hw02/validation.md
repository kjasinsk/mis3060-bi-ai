### 2A — Known-Answer Benchmarks (8 points)

Complete this table in `hw02/validation.md`. Every row must be filled in.

| Check | Expected | Your Script Produced | Match? | Notes |
|---|---|---|---|---|
| Dataset shape | (298772, 9) |(298772, 9) Yes | | |
| Null count — `security_id` | 101,597 |101,597 | Yes | |
| Null count — `amount` | 0 | 0 | Yes ||
| Unique `txn_type` values | 6 | 6 | Yes | |
| Count of `Buy` transactions | 83,556 | 83,556 | Yes | |
| `txn_date` data type | object | str | No |The data type for 'txn_date' is str (string).There is not even the word "object" in the script.|
| Earliest `txn_date` | 2020-01-01 | 2020-01-01 | Yes| |
| Latest `txn_date` | 2024-12-30 | 2024-12-30 | Yes | |
| Duplicate `txn_id` count | 0 | 0 | Yes | |
| Mean `amount` | $54,075.17 | $54,075.17 | Yes | |
| Median `amount` | $41,220.48 | $41,220.48 | Yes | |
| Skewness of `amount` | 1.15 | 1.15 | Yes | |
| Correlation `shares`–`amount` | 0.65 | 0.65 | Yes | |
| Correlation `price`–`amount` | 0.64 | 0.64| Yes | |
| Correlation `shares`–`price` | 0.00 | 0.00 | Yes| |
| Negative `shares` count (Buy only) | 836 | | | |
| Profile file created | Yes | | | |
| Chart files created (3) | Yes |  | | |

For any row where Match = No: describe the discrepancy and paste the Claude Cowork conversation you used to investigate it.
## 6. Follow-up question and answer

**My question:**
"For txn_date, Claude got object, but it is really string. What is the correct answer?"

**Claude's answer:**
"`str` is the correct one — that's exactly what printed in your terminal
(`txn_date             str`), and you're right that the word 'object' never
appears anywhere in the script itself.

Here's why the mismatch happened: in older/more common pandas setups, a
plain text column shows up as dtype `object` (that's been the standard
label for years). The fresh Claude session that walked through your script
predicted 'object' because it was reasoning from that typical default,
without having your actual data or knowing your exact pandas version. But
newer pandas versions can display text columns as `str` instead — either
because of a newer pandas release's default behavior, or a setting like
PyArrow-backed strings being enabled in your environment. Neither is
'wrong' as a concept (`str`/`object` both mean 'this column holds text, not
numbers'), but the specific label Claude predicted didn't match what your
environment actually printed.

So for your table row: prediction = `object`, actual = `str`, discrepancy
= Yes, and the explanation is essentially what you already wrote — Claude
assumed the traditional pandas label without knowing this environment's
pandas version shows text columns as `str` instead."

### 2B — Explain the Code and Output (16 points) 
1. Did Claude's predicted outputs (from Prompt 1) match what you actually saw in the terminal? List any discrepancies.

No not at all. At least Claude was honest that it was guessing since it didn't have the actual CSV yet. A few things it got wrong:

It assumed missing values would be zero across the board for "clean" data. In reality, security_id, shares, and price are each missing 101,597 values. 
It guessed security_id would be a whole-number column (int64). It's actually float64, because of those missing values.
It had the column order slightly wrong — txn_date actually comes before txn_type in the real file.
The example numbers it gave for the txn_type breakdown and unique counts (e.g., "8,412 unique clients") were made-up placeholders and didn't match the real numbers (2,700 unique clients).

The one thing that did match exactly: the shape, 298,772 rows × 9 columns — but that's because it pulled that number straight from the script's own EXPECTED_SHAPE variable, not because it predicted it.

2. What did Claude flag as potentially unexpected or worth investigating (from Prompt 2)?
security_id, shares, and price all cap out at exactly 500, and price has a suspiciously clean $10 floor — looks like simulated data rather than real trades.
Advisory Fee's mean ($7,375) is way higher than its median ($859), suggesting a few outlier fee amounts are skewing things.
All 836 negative shares values are under "Buy," never "Sell"." This is interesting because we would normally sell shares if the value is negative. 
client_id goes up to 3,192 but only 2,700 unique clients actually show up — worth checking against a client list.

It also pointed out the earlier FileNotFoundError and boxplot() errors were just environment/version issues, not data problems. This was because I was having trouble with creating the Claude files. 

3. Did Claude mention the 101,597 null values in security_id? What explanation did it give?

Yes. It explained the number isn't random. It matches the combined count of Deposit, Withdrawal, and Advisory Fee transactions exactly (35,981 + 29,850 + 35,766 = 101,597). 

4. Did Claude flag the txn_date column as a concern? Why would that matter for a time-series analysis?

Yes, it did point out that txn_date is stored as plain text, not an actual date type — so the min/max only works because every date happens to be formatted the same way (YYYY-MM-DD). For time-series work that matters because you can't do real date math on text — no calculating days between transactions, no grouping by month, no proper time-based plots — until you convert it with something like pd.to_datetime().

5. Open your three chart files. Does what you see in each image match Claude's explanation of that section of the output? Note any differences.
hist_amount.png — matches. Sharp peak near $0, long right tail, mean line sitting right of the median line — exactly what you'd expect from a positively skewed distribution.
box_amount_by_type.png — mostly matches. Advisory Fee is a tiny box with a big smear of outliers out to ~$140K, confirming the mean/median gap. One thing not obvious from the text output: Buy, Sell, and Dividend also have a ton of outlier points out to $250K, not just Advisory Fee.
scatter_shares_amount.png — mostly matches but with a real quirk: the legend lists six transaction types, but the chart is almost entirely one color (Buy) because it's plotted last and its points sit on top of everything else. The overall V-shape does confirm what the numbers said — amount stays positive regardless of whether shares are positive or negative.

6. Paste one follow-up question you asked Claude, and Claude's answer.
What do the best way to fix the Advisory Fee outliers? Is it better to remove them, leave them, or just make note of it?
Claude's Answer: Good question — and the honest answer is: don't remove them yet, investigate first, then decide.

### 2C — Business Check & Cross-Validation (16 points)

**Business-reasonableness questions.** Apply your knowledge of Wildcat Capital's business. Answer each question in your own words in `hw02/validation.md` — do not paste Claude's response as your answer here.

1. `security_id`, `shares`, and `price` are all null in exactly 101,597 rows. Looking at the `txn_type` value counts, which three transaction types would you expect to have no security — and why? Do the counts add up to 101,597?
I would expect the Deposit, Withdrawa, and Advisory fee are the 3 types with no security_id, Shares, and price because none of them are involved in buyin,selling or holding a specific security. They are cash-in, cash-out or a service charge. Yes, they add up (35,981+29,850+35,766)=101,597. 
2. There are 83,556 Buy transactions and 59,755 Sell transactions. What does it mean for a wealth management firm to have significantly more Buys than Sells over a five-year period?
If there are more buys, the firm is growing because they are accumulating more assets (and money) overtime. This wealth management firm must be in their growth phase as more people are buying with them than selling. AS new clients deposits, dividends that the clients obtan, get reinvested. 
3. The `txn_date` column is stored as a string (type `object`) rather than a date. If Claude Cowork generated code to compute the average number of days between transactions, what would go wrong if the dates remained as strings?
If the txn_date stays a string, the average days between transactions need actual calculations that average real time invervals to constantly update the values.
4. Wildcat Capital has 2,700 clients served by 25 advisors. Is that ratio — roughly 108 clients per advisor — plausible for a registered investment advisory firm? Honestly, after working at JP Morgan's Private Bank, I have learned at high-net worth individual often require a high attention requiring advisors to have around 30-75 clients per advisor. I do not beleve this is a reasonable for each advisor to have 108 clients. That is honestly, very overwhelming and it would be hard for advisor to manage all of these clients.  
5. 836 `Buy` transactions have negative `shares` values (as low as −499.63), while every other transaction type in the dataset has only positive share values. What are two plausible business explanations for a negative share count on a Buy transaction (for example, a data-entry sign error versus a legitimate correction or reversal entry), and what would you do next to determine which explanation is more likely?
There could be a negative share count because there is a data entry error where a value got flipped to a negative by mistake. Also, there could be a legitimate reversal where a buy gets cancelled, but it is logged as a negative instead of beig changed to a new diversifiaction type.


**Prompt A:** "Write Python to count rows in fact_transactions.csv where txn_type equals exactly 'Buy'."

```python
"""Prompt A: Write Python to count rows in fact_transactions.csv where txn_type equals exactly 'Buy'."""

import pandas as pd

df = pd.read_csv("data/raw/fact_transactions.csv")

buy_count = (df["txn_type"] == "Buy").sum()

print(f"Buy count (direct filter): {buy_count:,}")
```

**Prompt B:** "Write Python to count the total rows in fact_transactions.csv, then subtract the count of rows where txn_type is Sell, Deposit, Withdrawal, Dividend, or Advisory Fee."

```python
"""Prompt B: Write Python to count the total rows in fact_transactions.csv, then subtract the
count of rows where txn_type is Sell, Deposit, Withdrawal, Dividend, or Advisory Fee."""

import pandas as pd

df = pd.read_csv("data/raw/fact_transactions.csv")

total_rows = len(df)
other_types = ["Sell", "Deposit", "Withdrawal", "Dividend", "Advisory Fee"]
other_count = df["txn_type"].isin(other_types).sum()

buy_count_by_subtraction = total_rows - other_count

print(f"Total rows:            {total_rows:,}")
print(f"Rows in other 5 types: {other_count:,}")
print(f"Buy count (by subtraction): {buy_count_by_subtraction:,}")
```

**6. What did each script return?**

- Prompt A (direct filter): **83,556**
- Prompt B (subtraction): Total rows = 298,772; rows in the other five types = 215,216; 298,772 − 215,216 = **83,556**

**7. Do the results agree? If not, which one is wrong and why?**

Yes, both scripts return exactly 83,556. Since they agree, there's no evidence either one is wrong.

**8. Why is it useful to verify a count using subtraction rather than direct filtering?**

Because it is independent check rather than running the same logic twice. A direct filter and a subtraction approach can fail in different ways — a typo in the filter string, an unexpected extra category, or inconsistent text formatting in `txn_type` would likely throw off one method but not necessarily the other. Getting the same number from both methods is much stronger evidence the count is correct than getting the same answer from the same method run twice.

