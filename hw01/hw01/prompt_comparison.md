# Prompting Strategy Comparison

**Question tested:** "What are the most important metrics for measuring credit risk in a consumer loan portfolio?"

Each response below is capped at the first 150 words.

---

## Strategy 1 — Zero-Shot

**Technique:** Ask the question exactly as written, with no additional context.

**Response (150 words):**

The metrics that matter most for a consumer loan portfolio generally fall into a few groups, each answering a different question.

For borrower-level risk at origination, the core three are credit score (a summary of past repayment behavior), debt-to-income ratio (how much of a borrower's income is already committed to debt, which measures capacity to take on more), and loan-to-value ratio for secured loans like auto or home-related lending (how much cushion exists if the lender has to repossess and sell the collateral). Income itself matters mostly as a scale check rather than a risk signal on its own.

For the portfolio as a whole, the standard health metrics are the default rate (share of loans that have gone to loss), the delinquency rate broken into stages like 30/60/90 days past due (an early-warning view of loans heading toward trouble), and the roll rate or migration rate — what share …

---

## Strategy 2 — Role-Assigned (Role + Audience)

**Technique:** "You are a senior credit risk analyst at JP Morgan presenting to the US Treasury on credit metrics in your excel file. Answer this question for them: 'What are the most important metrics for measuring credit risk in a consumer loan portfolio?'"

**Response (150 words):**

Credit Risk Metrics for a Consumer Loan Portfolio

Thank you for the opportunity to walk through this. When we evaluate credit risk in a consumer loan portfolio, we look at it in layers — borrower-level underwriting metrics, portfolio-level performance metrics, loss-severity metrics, and forward-looking indicators. No single number tells the full story, so we rely on this framework together.

At the borrower level, the three metrics that carry the most underwriting weight are credit score, debt-to-income ratio, and loan-to-value ratio for secured products. Credit score is our best single predictor of repayment behavior because it reflects a track record over time. DTI measures a borrower's current capacity to absorb additional debt, independent of history. LTV, where collateral is involved, tells us how much of our exposure is actually protected if a loan goes bad. We treat these as complementary rather than interchangeable — a strong score doesn't offset an unsustainable …

---

## Strategy 3 — Few-Shot

**Technique:**

> Here's the format I want you to use:
>
> Point: [a short label for the idea]
> Explanation: [one to two sentences explaining it]
> Why it matters: [one sentence on the practical implication]
>
> (That's just the format — not a real answer.)
>
> Now, using that exact format, answer: "What are the most important metrics for measuring credit risk in a consumer loan portfolio?"

**Response (150 words):**

**Point:** Credit Score
**Explanation:** A summary of a borrower's historical repayment behavior, derived from prior credit accounts, payment timeliness, and credit utilization.
**Why it matters:** It's the single strongest predictor of default risk at the point of underwriting.

**Point:** Debt-to-Income Ratio (DTI)
**Explanation:** The share of a borrower's income already committed to debt payments before any new loan is added.
**Why it matters:** It measures current capacity to take on more debt, independent of credit history, so it catches borrowers who are stretched thin even with a good score.

**Point:** Delinquency Rate (by aging bucket: 30/60/90 days past due)
**Explanation:** The share of loans currently behind on payments, broken out by how far behind they are.
**Why it matters:** It's a leading indicator — it shows where the default rate is likely headed before that loss actually materializes.

**Point:** Roll Rate / Migration Rate
**Explanation:** The pace at which loans …
## Conclusion

The zero-shot response was generic and not tailored to the exact situation the Treasury needed. The role-assigned prompt produced the most polished response because the stakes were higher than a routine answer — the audience was leadership, not just a standard reader. Strategy 3 (few-shot) was well organized and surfaced many individual rates, making it ideal for an analyst to grab quick points from, but the outputs don't carry much detail on their own — an analyst would need to build a larger conclusion and add more context before presenting it to leadership. Overall, the role-assigned version is the better choice because it explicitly accounts for the audience the information needs to be catered to.

## Fact-Check

**Claim source:** Part 3, Strategy 1 — Zero-Shot (the question was asked exactly as written, with no additional context, role, or format instructions). Question tested: "What are the most important metrics for measuring credit risk in a consumer loan portfolio?" The claim appears in the first main paragraph, where Claude explains the three borrower-level underwriting metrics — credit score, DTI, and LTV.

**The exact claim Claude made:**

> "...loan-to-value ratio for secured loans like auto or home-related lending (how much cushion exists if the lender has to repossess and sell the collateral)..."

**The source used and the URL:**

CFPB — "What is a loan-to-value ratio and how does it relate to my costs?"
https://www.consumerfinance.gov/ask-cfpb/what-is-a-loan-to-value-ratio-and-how-does-it-relate-to-my-costs-en-121/

**What the source says:**

The CFPB defines LTV as "a measure comparing the amount you are financing with the appraised value of the property." A higher LTV means less equity behind the loan and more risk to the lender (often resulting in a higher interest rate or a requirement for mortgage insurance), while a lower LTV means the collateral provides more protection if the borrower defaults.

**Whether they agree, and what that says about reliability:**

They basically agree. What Claude said — that LTV measures how much cushion a lender has if it ends up repossessing and selling the collateral. This lines up almost exactly with how the CFPB explains it: the lower the LTV, the more equity sits between the loan balance and what the collateral is actually worth, and that gap is the cushion Claude was describing.

The CFPB page is written specifically about mortgages and real estate, but Claude applied the same idea to auto loans too. Overall, this is a good sign for Claude's reliability on definitional claims like this one; it got the underlying mechanism right. However, it is still vital that we verify the information that Claude gives us. 
