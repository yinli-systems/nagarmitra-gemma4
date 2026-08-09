# NagarMitra: the next safe step for every street-level problem

**Subtitle:** A local-first civic action agent for Prayagraj, powered by Gemma 4.

**Track:** The GenAI for Good Track

## The problem

For a resident, “the garbage has not been collected”, “this streetlight is broken”, or “the water looks strange” is not an AI question. It is a handoff problem. The resident has evidence, but not always the right department, language, form, or network connection. Existing chatbots often make that handoff worse: they invent phone numbers, overstate certainty, or hide the important steps inside a fluent paragraph.

NagarMitra is designed for the moment before a complaint is submitted. A resident or community worker can select a civic issue, add a short message and a photo, and receive a reviewable action card in Hindi or English. The card says what was observed, how urgent a response may be, which desk is relevant, what evidence is still needed, and which official sources support the recommendation.

## What the demo shows

The live prototype at [yinli-systems.github.io/nagarmitra-gemma4](https://yinli-systems.github.io/nagarmitra-gemma4/) has three visible stages:

1. **Intake:** a short report, privacy-safe landmark, optional image, and language choice.
2. **Agent trace:** Gemma 4 classifies the report, calls an allow-listed department lookup, retrieves source-backed guidance, drafts a bilingual card, and runs a safety review.
3. **Human handoff:** the result contains urgency, department, confidence, a checklist, and source links. A reviewer must explicitly approve it before it can enter the offline queue. There is no automatic submission button.

The three prepared cases are overflowing waste, a broken streetlight, and possible water contamination. They are intentionally ordinary: the value is not a spectacular chatbot answer, but a safer and more accountable next step that a local worker can actually use.

## Why Gemma 4 is core

Gemma 4 is not used as decoration around a hard-coded response. It is the intelligence layer in the model-backed path in [`gemma4_agent.py`](https://github.com/yinli-systems/nagarmitra-gemma4/blob/main/gemma4_agent.py):

- It interprets a resident's short, multilingual description and can accept an optional image through the Transformers processor.
- It receives explicit function declarations for `lookup_department`, `get_official_guidance`, and `draft_complaint`.
- Its native tool-call output is parsed, validated, and mapped to deterministic local Python functions.
- The tool responses are appended to the conversation, after which Gemma 4 writes the final resident-facing action card.

The three functions are the only execution surface. The allow-list rejects unknown tool names and invalid arguments. The knowledge base is versioned in [`data/knowledge.json`](https://github.com/yinli-systems/nagarmitra-gemma4/blob/main/data/knowledge.json), so the model cannot turn a plausible guess into a fabricated contact or policy. The complaint function returns `send: false` by design.

The attached [Kaggle Notebook](https://www.kaggle.com/code/kevin250304/nagarmitra-gemma-4-civic-action-agent) runs a parser and allow-list smoke test before loading the mounted Gemma 4 resource. It then executes the real model-backed flow on a GPU. The static demo is a deterministic presentation harness so the complete UX remains inspectable even when a model download is slow; the Python module is the source of truth for actual Gemma integration.

## Safety and dignity by construction

NagarMitra makes four safety choices visible to the person using it:

- **No diagnosis:** a water report triggers “pause use and request testing”, never a health conclusion.
- **No fabricated contacts:** the app shows official source records, not a generated phone number.
- **Landmark, not private address:** the intake asks for an approximate public place.
- **Human approval:** the resident owns the final complaint. Offline queueing is a convenience, not consent to send.

These constraints are part of the product behavior, not only prompt text. They are enforced by the tool boundary, the local data model, and the UI approval gate.

## What makes this different

The existing civic-assistant pattern is usually “ask a question and get an answer”. NagarMitra treats civic access as an evidence-to-action workflow. It combines multimodal understanding, structured tool use, local grounding, bilingual output, offline-first behavior, and an explicit human handoff. The agent trace is deliberately exposed: a judge can see where Gemma 4 was used, which local tools were called, and where the system refused to act.

## Limitations and next step

This is a hackathon prototype, not a municipal deployment. The source records are a small, curated starting set. A real rollout would require authenticated municipal adapters, consented location capture, accessibility testing with local users, local-language evaluation, and an operations owner for updating source records. Those additions are intentionally outside the prototype so that the current demo stays reproducible and fail-closed.

## Project links

- [Public source repository](https://github.com/yinli-systems/nagarmitra-gemma4)
- [Live Demo](https://yinli-systems.github.io/nagarmitra-gemma4/)
- [Clonable Kaggle Notebook](https://www.kaggle.com/code/kevin250304/nagarmitra-gemma-4-civic-action-agent)
- [Gemma 4 function calling documentation](https://ai.google.dev/gemma/docs/capabilities/text/function-calling-gemma4)

