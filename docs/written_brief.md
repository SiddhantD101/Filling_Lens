# FilingLens Written Brief

## Area explored

I explored whether AI can help people read company filings after an oil, fuel, or currency shock. The part that interested me most was not prediction. It was the quieter question: did the company clearly explain the exposure, or did it leave the reader to infer too much?

What surprised me was how useful a negative finding can be. If a company shows a large fuel or import cost, but does not explain what a price move would do to profit, that absence is itself important. It is also hard to present well. A raw table of extracted facts quickly becomes clutter, so the product needs to translate filings into plain language first, then let a reviewer inspect the source only when needed.

## Problem statement

The user is an analyst, credit reviewer, finance team member, or diligence reviewer who needs to understand risk disclosures across many companies.

The task is to answer, for each company:

1. What exposure did the company disclose?
2. Where did it say that?
3. Did it explain what happens if oil, fuel, or exchange rates move?
4. Is anything missing, stale, conflicting, or suspicious?

This work happens whenever markets move sharply, when quarterly or annual reports are released, or when a portfolio review is due. In a real team this could happen weekly during volatile periods, and more heavily during earnings season.

The cost today is mostly analyst time and missed consistency. Someone has to search filings, copy numbers into a spreadsheet, remember which companies were already checked, and explain why a report was trusted or not trusted. The expensive part is not only reading. It is proving where the answer came from and avoiding false confidence.

## What I built

I built FilingLens, a working prototype that reads filing style text, extracts oil, fuel, and FX exposure facts, verifies them against source quotes, flags disclosure gaps, and shows the result in a React workspace.

The product has four main parts:

1. A plain English home view that says what needs attention.
2. A reports view that starts with a simple summary before showing evidence.
3. A review inbox where a human can accept, reject, or mark items for follow up.
4. A comparison view that shows which companies have larger visible exposure and which reports look incomplete.

There is also a chat style copilot. It answers from the loaded reports first. If the question cannot be answered from local data, it can call an external model when an API key is configured.

## What I added beyond the AI

The AI is not treated as the source of truth. The important product work is around the AI:

1. A fixed schema for the facts we care about.
2. Page level storage so every answer can point back to source text.
3. Verification that checks whether a quote and number actually appear in the source.
4. Rules that flag missing sensitivity, stale disclosures, conflicting values, and suspicious source text.
5. A human review layer with accept, reject, and follow up decisions.
6. A simpler UI that hides internal scan details and shows the user what matters first.

The prototype also has a deterministic baseline extractor. That matters because it gives a reproducible floor. The intended AI path can be plugged into the same schema, but code still verifies the output afterward.

## Solution design

The design separates reading from checking. AI can help read messy filing language, but final status should come from code and human review.

```text
Company filing text
        |
        v
Page parser and storage
        |
        v
Candidate page retrieval
        |
        v
Extractor
  AI or deterministic baseline
        |
        v
Verifier
quote present, number present, unit checked
        |
        v
Gap rules
missing explanation, stale date, conflict, unusual text
        |
        v
FilingLens workspace
summary, evidence, review inbox, comparison
        |
        v
Human reviewer
accept, reject, follow up
```

The human acts at the points where judgement matters: deciding whether a missing disclosure is material, whether a quote is enough, and whether an item should be shared. The AI acts only in the narrow reading step: finding and transcribing relevant disclosure text.

The current prototype uses SQLite for persistence and a Python API for analysis and review actions. The frontend is a React app. The model path is optional through OpenRouter. The local baseline works without any key.

## Alternatives rejected

I rejected an end to end prediction tool because it would look more precise than the filings support. Forecasting profit impact would require assumptions about hedges, pass through, pricing power, volumes, and timing. That is not safe to infer from short disclosure excerpts.

I also rejected a pure chatbot as the main interface. A chatbot is helpful for questions, but it does not give a stable review workflow, evidence status, peer comparison, or audit trail.

A pure regex tool was useful as a baseline, but too brittle as the final answer. Filing language varies too much. The better design is a narrow AI extraction step with strict verification after it.

I also avoided a complex multi agent setup. This problem needs traceability more than orchestration. A smaller pipeline is easier to test and explain.

## Risks and mitigations

Wrong answers are the main risk. The design handles this by requiring source quotes, checking that extracted numbers are present or directly implied, and routing uncertain items to human review.

Outdated rules are another risk. Disclosure expectations and materiality thresholds may change by sector, region, or user. The prototype keeps shock dates and thresholds in config so they can be changed without rewriting the product.

Confidential data is a risk if private filings or internal notes are uploaded. The prototype uses public or synthetic text only. A production version should add access control, retention rules, redaction, and clear separation between customers.

Liability is a serious risk. FilingLens should not give investment advice or predict share prices. It should say what the report disclosed, what was not clear, and what a human should review.

Prompt injection and hostile source text are also relevant because filings may contain text that should not control the system. The prototype flags suspicious instruction like wording in source text and treats source documents as data, not commands.

The hardest risk is a false missing disclosure. If retrieval misses the right page, the system may say something was not disclosed. That is why missing items should be shown as review items, not final accusations.

## What I would consider before spending more time

Before investing more time, I would want to test the idea on real public annual reports. Synthetic examples are useful for proving the pipeline, but the product only becomes convincing when it handles real filing language.

I would also talk to one or two actual users. The key question is whether they care more about exposure size, missing sensitivity, stale disclosures, peer comparison, or source auditability.

I would check whether the same workflow should focus on oil and FX only, or whether the better wedge is broader disclosure quality review. The product may be more useful as a general filing review layer than as a narrow commodity risk tool.

Finally, I would define what a good output looks like for a real user. If the goal is a report, the export matters. If the goal is review, assignment and sign off matter. If the goal is research, source coverage and recall matter most.
