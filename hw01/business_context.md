# Part 2: Business Context Exploration

## Questions

1. Wildcat underwrites primarily on credit score, debt-to-income ratio, and annual income. What does each of those actually capture about a borrower's risk that the others don't, and where would you expect them to disagree — for example, a borrower with a strong credit score but a high DTI, or high income paired with a thin credit history? How should underwriting weigh those metrics against each other rather than treating them as interchangeable?

2. For a lender with Wildcat's loan-purpose mix — Auto, Personal, Home Improvement, Education, and Business — what would a portfolio committee typically expect to see in a quarterly review? Think beyond a single blended default rate: what kinds of breakdowns (by purpose, vintage, credit tier) and what forward-looking indicators would let the committee catch a problem before it shows up in the headline numbers?

3. Wildcat's loan_status field has four categories: Current, Delinquent, Default, and Paid Off. What's the substantive difference between delinquency and default, and at what point does a loan typically move from one to the other? What does that distinction suggest about how a committee should generally read a Delinquent bucket — is it usually a leading indicator worth monitoring closely, or closer to a rounding error next to the Default number?

## Responses

**1. Credit metrics:** Credit score reflects past repayment behavior, DTI measures current capacity to take on more debt, and income measures the size of a borrower's overall cushion — each one captures something the others miss. They disagree in predictable ways: a strong score with high DTI signals someone stretched thin despite a clean history, while high income with a weak credit file is hard to trust because there's little behavioral evidence behind it. Underwriting shouldn't average these together; score should anchor the risk tier, DTI should act as a capacity cap, and income should mainly serve as an affordability check rather than something that offsets a weak score.

**2. Portfolio committee review:** A blended default rate hides too much across five loan purposes that behave very differently, so a committee needs default and delinquency rates broken out by purpose, especially since Business loans are larger and fewer, and can drive dollar losses disproportionately to their loan count. A vintage view (default/delinquency by origination period) shows whether recent originations are riskier than older ones — an early sign underwriting standards may have loosened. Credit-tier composition by purpose flags where risk is concentrating, and forward-looking indicators like the delinquency rate, Current-to-Delinquent migration, and dollar concentration matter more than trailing default numbers for catching problems early.

**3. Delinquency vs. default:** Delinquency means a borrower has missed payments but the loan is still considered collectible, while default means the lender has concluded it's a loss and written it off — the move between them usually happens after a sustained period of nonpayment (commonly around 90 days), passing through stages along the way. Because defaults are drawn from the pool of delinquent loans, delinquency is generally a leading indicator rather than noise. A committee that watches only the Default number is looking at a lagging metric and would miss the early warning the Delinquent bucket provides.

## Follow-Up Question

*Given that Business loans are a small share of loan count but a disproportionate share of dollar exposure, does Wildcat have a concentration limit on Business lending — and if not, what would trigger the committee to set a limit?*
