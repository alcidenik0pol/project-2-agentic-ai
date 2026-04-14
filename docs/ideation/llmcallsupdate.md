Two prompts need changing.
Call 7 — Hypothesis Generation (app/analyst/hypothesis_prompts.py)
This is the main offender. The phrase "business analyst" and "business opportunities" is baking in the output framing. Change:

"You are a business analyst specializing in identifying unmet market needs" → "You are an analyst identifying unmet needs and gaps from social data"
"identify the top 5 most actionable business opportunities" → "identify the top 5 most actionable solutions or concepts that directly address the complaints"
"product_description" in the schema → "solution_description" — "business product" language is leaking through the field names too
The instruction "Be specific: 'app that does X' not 'platform that helps people with Y'" is directly biasing toward software products. Remove it entirely.

That's it for Call 7. Everything else in that prompt is fine — the evidence anchoring, the schema structure, the confidence reasoning are all solid.
Call 1 — Orchestrator (app/agents/orchestrator.py)
Smaller change but worth it. "Reddit complaint analysis system" appears twice and frames the entire fetch around negativity. Posts expressing desire or wishful thinking are equally valuable signal but would get deprioritized or filtered out downstream. Change it to "Reddit signal analysis system" and adjust the handoff summary instruction to mention both complaints and expressed desires/gaps.