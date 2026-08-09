"""NagarMitra's real Gemma 4 tool-calling path.

This file is intentionally separate from the static presentation harness. The
static page can be judged without a model download; this module is the
reproducible source of truth for the model-backed agent.

The implementation follows the public Gemma 4 Transformers tool-calling
protocol. All tool execution is allow-listed and local.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parent
KNOWLEDGE_PATH = ROOT / "data" / "knowledge.json"


def load_knowledge() -> dict[str, dict[str, Any]]:
    with KNOWLEDGE_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def lookup_department(issue_type: str, district: str = "Prayagraj") -> dict[str, Any]:
    """Look up a responsible civic desk from the local, versioned knowledge base."""

    knowledge = load_knowledge()
    if issue_type not in knowledge:
        return {"ok": False, "error": "Unknown issue type; human routing is required."}
    item = knowledge[issue_type]
    return {
        "ok": True,
        "district": district,
        "issue_type": issue_type,
        "department": item["department"],
        "department_hi": item["department_hi"],
        "sources": item["sources"],
    }


def get_official_guidance(issue_type: str) -> dict[str, Any]:
    """Return safety and evidence guidance without inventing medical or legal advice."""

    knowledge = load_knowledge()
    if issue_type not in knowledge:
        return {"ok": False, "error": "No verified guidance is available for this issue."}
    item = knowledge[issue_type]
    return {
        "ok": True,
        "issue_type": issue_type,
        "urgency": item["urgency"],
        "reason": item["reason"],
        "reason_hi": item["reason_hi"],
        "checklist": item["checklist"],
        "sources": item["sources"],
    }


def draft_complaint(
    issue_type: str,
    report: str,
    place: str,
    language: str = "hi",
) -> dict[str, Any]:
    """Create a reviewable complaint draft; this function never sends it."""

    knowledge = load_knowledge()
    if issue_type not in knowledge:
        return {"ok": False, "error": "Cannot draft an unclassified issue."}
    item = knowledge[issue_type]
    language = language if language in {"hi", "en"} else "en"
    if language == "hi":
        summary = f"{item['hindi_label']} की सूचना मिली है। स्थान: {place}. विवरण: {report}"
        review_note = "यह केवल समीक्षा के लिए मसौदा है; भेजने से पहले निवासी सत्यापित करें।"
    else:
        summary = f"Reported {item['label'].lower()} at {place}. Details: {report}"
        review_note = "Draft for human review only; the resident must verify before sending."
    return {
        "ok": True,
        "subject": item["label"],
        "summary": summary,
        "department": item["department_hi"] if language == "hi" else item["department"],
        "urgency": item["urgency"],
        "review_note": review_note,
        "send": False,
    }


TOOL_DECLARATIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "lookup_department",
            "description": "Find the responsible civic desk using only the local verified knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_type": {
                        "type": "string",
                        "enum": ["garbage_overflow", "broken_streetlight", "unsafe_water"],
                    },
                    "district": {"type": "string", "description": "Indian district, default Prayagraj."},
                },
                "required": ["issue_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_official_guidance",
            "description": "Retrieve source-backed urgency and safety guidance for a known civic issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_type": {
                        "type": "string",
                        "enum": ["garbage_overflow", "broken_streetlight", "unsafe_water"],
                    }
                },
                "required": ["issue_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_complaint",
            "description": "Prepare a bilingual complaint draft for a human to review. Never submit it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_type": {"type": "string", "enum": ["garbage_overflow", "broken_streetlight", "unsafe_water"]},
                    "report": {"type": "string"},
                    "place": {"type": "string"},
                    "language": {"type": "string", "enum": ["hi", "en"]},
                },
                "required": ["issue_type", "report", "place", "language"],
            },
        },
    },
]


TOOL_IMPLS: dict[str, Callable[..., dict[str, Any]]] = {
    "lookup_department": lookup_department,
    "get_official_guidance": get_official_guidance,
    "draft_complaint": draft_complaint,
}


def _cast(value: str) -> Any:
    value = value.strip().strip('"').strip("'")
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        return value


def extract_tool_calls(text: str) -> list[dict[str, Any]]:
    """Parse Gemma 4's special-token tool calls without evaluating model output."""

    calls: list[dict[str, Any]] = []
    pattern = re.compile(r"<\|tool_call\|?>call:(\w+)\{(.*?)\}<tool_call\|>", re.DOTALL)
    for name, raw_args in pattern.findall(text):
        arguments: dict[str, Any] = {}
        # Gemma's simple tool-call grammar separates arguments with commas and
        # marks quoted values as <|"|>value<|"|>.
        for chunk in re.split(r",\s*(?=\w+:)", raw_args):
            if ":" not in chunk:
                continue
            key, value = chunk.split(":", 1)
            value = value.replace('<|"|>', "").strip()
            arguments[key.strip()] = _cast(value)
        calls.append({"name": name, "arguments": arguments})
    return calls


def execute_allowlisted(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Execute only known tools with known arguments; unknown calls fail closed."""

    results = []
    for call in calls:
        name = call.get("name", "")
        implementation = TOOL_IMPLS.get(name)
        if implementation is None:
            results.append({"name": name, "response": {"ok": False, "error": "Tool is not allow-listed."}})
            continue
        try:
            response = implementation(**call.get("arguments", {}))
        except (TypeError, ValueError) as error:
            response = {"ok": False, "error": f"Invalid tool arguments: {error}"}
        results.append({"name": name, "response": response})
    return results


class Gemma4Agent:
    """Thin Transformers runner for a mounted Gemma 4 instruction model."""

    def __init__(self, model_id: str | None = None):
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoProcessor
        except ImportError as error:  # pragma: no cover - depends on Kaggle runtime
            raise RuntimeError("Install transformers, accelerate, torch, and pillow in the Kaggle notebook first.") from error

        self.torch = torch
        self.model_id = model_id or os.environ.get("GEMMA_MODEL_ID", "")
        if not self.model_id:
            raise RuntimeError("Set GEMMA_MODEL_ID to the mounted Gemma 4 model resource; refusing an unverified fallback.")
        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype=dtype,
            device_map="auto",
        )

    def _generate(self, messages: list[dict[str, Any]], image_path: str | None = None) -> str:
        images = None
        if image_path:
            from PIL import Image

            images = [Image.open(image_path).convert("RGB")]
        prompt = self.processor.apply_chat_template(
            messages,
            tools=TOOL_DECLARATIONS,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self.processor(text=prompt, images=images, return_tensors="pt")
        device = next(self.model.parameters()).device
        inputs = {key: value.to(device) if hasattr(value, "to") else value for key, value in inputs.items()}
        with self.torch.inference_mode():
            output = self.model.generate(**inputs, max_new_tokens=512, do_sample=False)
        generated = output[0][inputs["input_ids"].shape[-1] :]
        return self.processor.decode(generated, skip_special_tokens=False)

    def run(
        self,
        report: str,
        place: str,
        language: str = "hi",
        image_path: str | None = None,
    ) -> dict[str, Any]:
        system = (
            "You are NagarMitra, a careful civic action assistant for Prayagraj. "
            "Classify only one of the known issue types. Use approved tools before answering. "
            "Never diagnose, invent phone numbers, expose private addresses, or submit a complaint. "
            "Return a short bilingual action card with the source titles and a human-review warning."
        )
        user = f"Resident report: {report}\nApproximate landmark: {place}\nPreferred language: {language}"
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        first_output = self._generate(messages, image_path=image_path)
        calls = extract_tool_calls(first_output)
        results = execute_allowlisted(calls)
        trace = [{"tool": call["name"], "arguments": call["arguments"], "response": result["response"]} for call, result in zip(calls, results)]
        if not calls:
            return {"trace": [], "answer": first_output, "warning": "Gemma returned no approved tool call; no action was taken."}

        messages.append({
            "role": "assistant",
            "tool_calls": [{"function": call} for call in calls],
            "tool_responses": results,
        })
        final_output = self._generate(messages)
        return {"trace": trace, "answer": final_output, "tool_calls": calls, "model_id": self.model_id}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the NagarMitra Gemma 4 agent")
    parser.add_argument("--case", default="garbage_overflow", choices=["garbage_overflow", "broken_streetlight", "unsafe_water"])
    parser.add_argument("--report", default="कूड़ा तीन दिन से नहीं उठा है और नाली बंद हो रही है।")
    parser.add_argument("--place", default="Naini, near school gate")
    parser.add_argument("--language", default="hi", choices=["hi", "en"])
    parser.add_argument("--image", default=None, help="Optional local image path for Gemma 4 multimodal input")
    parser.add_argument("--model-id", default=None, help="Mounted Gemma 4 model path; otherwise GEMMA_MODEL_ID")
    parser.add_argument("--print-schema", action="store_true")
    args = parser.parse_args()
    if args.print_schema:
        print(json.dumps(TOOL_DECLARATIONS, ensure_ascii=False, indent=2))
        return
    result = Gemma4Agent(model_id=args.model_id).run(args.report, args.place, args.language, args.image)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
