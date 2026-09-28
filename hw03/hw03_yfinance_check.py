"""
HW3 Part 5C - Cross-check Apple's quarter ended June 27, 2026 using yfinance.
Run:  python hw03_yfinance_check.py   (pip install yfinance first if needed)
"""
import yfinance as yf

stmt = yf.Ticker("AAPL").quarterly_income_stmt   # columns = quarter-end dates, newest first

print("Quarters available:", [str(c.date()) for c in stmt.columns])
for row in ["Total Revenue", "Net Income", "Diluted EPS"]:
    if row in stmt.index:
        value = stmt.loc[row].iloc[0]           # most recent quarter
        if row == "Diluted EPS":
            print(f"{row}: ${value:.2f}")
        else:
            print(f"{row}: ${value / 1e6:,.0f} million")
print("Quarter shown above ends:", stmt.columns[0].date())
