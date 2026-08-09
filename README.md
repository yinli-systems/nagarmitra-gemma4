# NagarMitra — a local-first civic action agent powered by Gemma 4

NagarMitra helps a resident or community worker turn a photo, voice transcript, or short message into a **reviewable civic action card**: issue category, urgency, responsible department, evidence checklist, and a complaint draft in the resident's language.

The prototype is designed for the **GenAI for Good** track of [Build with Gemma: TFUG Prayagraj](https://www.kaggle.com/competitions/build-with-gemma-tfug-prayagraj-ai-prayagraj). It is deliberately local-first:

- Gemma 4 is the reasoning and multimodal understanding layer.
- Function calls are restricted to an allow-list of deterministic local tools.
- Every factual recommendation points to a source record in `data/knowledge.json`.
- A ticket is saved to an offline queue and is never silently submitted on a resident's behalf.

## Run the demo

The static demo needs no API key and works offline. It uses the same trace and knowledge records as the live presentation flow.

```bash
python3 -m http.server 8000
```

Open <http://127.0.0.1:8000>.

Choose one of the three demo cases, change the language, and select **Analyze with Gemma 4**. The UI makes the agent trace, source cards, safety gate, and offline queue visible instead of presenting an opaque chatbot.

## Run the real Gemma 4 agent

The model-backed implementation is in [`gemma4_agent.py`](gemma4_agent.py). It follows the official Gemma 4 Transformers tool-calling protocol: render the chat template with tools, parse the model's structured tool call, execute only an allow-listed function, append the tool response, and ask Gemma for the final resident-facing answer.

On Kaggle, attach an accessible Gemma 4 model resource to a GPU notebook and set its mounted model path:

```bash
pip install -U transformers accelerate torch pillow
export GEMMA_MODEL_ID=/kaggle/input/<attached-gemma-4-resource>/
python gemma4_agent.py --case garbage_overflow --language hi
```

If no model path is provided, the script fails closed with an actionable message; it never falls back to a different hosted model and claim that it is Gemma.

## Evidence boundary

The static UI is a deterministic presentation harness so judges can inspect the complete interaction without a network or a model download. The Python path is the source of truth for the actual Gemma 4 integration. A production deployment would add authenticated municipal API adapters, consented location capture, accessibility testing with local users, and an explicit human approval step before submission.

## Project links

- Competition: [Build with Gemma: TFUG Prayagraj](https://www.kaggle.com/competitions/build-with-gemma-tfug-prayagraj-ai-prayagraj)
- Gemma 4 function calling: [Google AI for Developers](https://ai.google.dev/gemma/docs/capabilities/text/function-calling-gemma4)
- Gemma 4 model card: [Google AI for Developers](https://ai.google.dev/gemma/docs/core/model_card_4)
- License: Apache 2.0

