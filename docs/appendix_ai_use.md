# Appendix: What Was Added Beyond AI

## Where AI Helped

AI helped turn the idea into an implementation plan, scaffold the prototype modules, draft test cases and write first-pass submission text.

Example prompts to include in the final LLM log:

- "Given this finance assignment and my Disclosure Gap Finder plan, map the plan to a minimal prototype repo."
- "Create labelled test cases that probe fuel and FX disclosure extraction failures."
- "Review this architecture for auditability, false non-disclosure risk and human-in-the-loop controls."

## What Was Rejected Or Corrected

Generic suggestions to forecast EPS impact were rejected because disclosed sensitivities often do not represent full operating exposure. A model-generated confidence score was rejected because the design needs verifier-driven status, not model self-belief. A chatbot interface was rejected because it would make outputs hard to compare and audit.

## What Came From Me

The strongest product decision is to treat non-disclosure as a first-class finding. The tool is useful not because it claims to know the economic truth, but because it shows what the company did and did not say. The second key decision is to drop any headline "impact" number unless it is directly disclosed and quoted.

## One Thing I Would Defend Without AI

The exact-versus-probabilistic split: let AI read varied language, but let code verify quotes, numbers, units, status and gap rules. This is the core reason the design can be audited.
