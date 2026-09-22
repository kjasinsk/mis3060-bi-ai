# EDA Script Specification

Hey — here's what we need for this project. I'll walk you through it the way
I'd explain it if you were sitting next to me.

## The big picture

We've got a transactions dataset sitting at `data/raw/fact_transactions.csv`,
and we need to get a solid first look at it — the kind of exploratory data
analysis (EDA) you'd do before trusting a dataset enough to build anything
on top of it. The catch: it all needs to live in **one Python script**. Not
a notebook with cells you run one at a time, not a handful of smaller
scripts — one file that you run once, and it does everything from loading
the data to saving the charts. Think of it as a self-contained "give me the
full picture" tool.

## Walking through what the script needs to do

Start by loading `data/raw/fact_transactions.csv` into a pandas DataFrame —
that's the only input file you'll need.

From there, work through the following, roughly in this order, printing
things to the console as you go so whoever runs it can follow along:

First, give us the basics: **how big is this thing** — print the shape, so
rows and columns. Then **walk through the columns** — print each column's
name next to its data type, so we know what we're working with before we
go any further.

Next, a data-quality pass: **print how many values are missing in each
column**. That's usually the first thing that tells you if something's off
with the data.

Then get into the numbers: **print descriptive statistics for every numeric
column** — count, mean, standard deviation, min, 25th percentile, median,
75th percentile, and max. That's your standard `describe()`-style summary.

Since `txn_type` is clearly a key category here, **print a breakdown of it**
— value counts and percentages, sorted with the most common type first and
the least common last.

We'll also want a sense of scale on the entity side, so **print how many
unique clients, advisors, and securities** show up in the file.

Time matters too — **print the earliest and latest `txn_date`** so we know
what period this dataset actually covers.

Data hygiene check: **look for duplicate rows based on `txn_id`** and print
how many you find. If it's zero, great, but we need to confirm that, not
assume it.

Now dig into the `amount` column specifically — **print its mean, median,
and skewness**. Skewness especially will tell us if this is a normal-ish
distribution or something more lopsided.

Go a level deeper and **group the data by `txn_type`**, and for each group
print the count of transactions plus the mean and median amount, rounded to
2 decimal places. Sort the groups so the highest average amount comes first.

Then look at how `shares`, `price`, and `amount` relate to each other —
**compute and print the correlation matrix** for those three columns,
rounded to 2 decimal places. Don't just dump the matrix and move on, though
— explicitly call out **the three strongest correlations**, and make sure
you exclude a variable's correlation with itself (that's always 1.0 and
tells us nothing).

One more breakdown: **for each `txn_type`, print the minimum, maximum, and
count of negative values in the `shares` column**. Negative shares might be
totally normal for certain transaction types (like sells) or might flag a
data issue — this step helps us see which.

Build in a sanity check too: **if the DataFrame's shape isn't exactly
(298772, 9), print a clear warning** saying so. We want this to be
impossible to miss if the data doesn't match what we expect.

## Charts

Save three charts into a `hw02/charts/` folder (create the folder if it
doesn't exist yet):

- A **histogram of `amount`**, with vertical lines marking the mean and the
  median — label them clearly so it's obvious which line is which. Save it
  as `hw02/charts/hist_amount.png`.
- A **horizontal box plot of `amount`, broken out by `txn_type`**. Save it
  as `hw02/charts/box_amount_by_type.png`.
- A **scatter plot of `shares` (x-axis) vs. `amount` (y-axis)**, with points
  colored by `txn_type`. Save it as `hw02/charts/scatter_shares_amount.png`.

## Save a written summary

Take everything that got printed for the stats steps — shape, column
info, missing values, descriptive statistics, the `txn_type` breakdown,
unique counts, date range, duplicate check, amount stats, the grouped
amount stats, the correlation matrix, and the shares-by-type breakdown —
and also save it as a plain-text file at `hw02/hw02_profile.txt`. That way
we have a copy we can hand off or reference later without re-running
anything.

## Don't forget the header

At the very top of the script, add a comment block that says what the
script is, what dataset it uses (`data/raw/fact_transactions.csv`), who
wrote it (a placeholder like `[Your Name]` is fine if we don't have a name
yet), and the date it was generated. Small thing, but it makes the script
self-documenting.

## The one rule that matters most

All of this — every step above — needs to happen in **a single script, in
one run**. Not seventeen scripts, not a step-by-step notebook. Someone
should be able to run this one file, sit back, and get the console output,
the three chart images, and the text summary, all from one execution,
without touching anything by hand (as long as the CSV is sitting where it's
supposed to be).

