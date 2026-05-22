import os
import re
import json
import sys
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
PORT = int(os.getenv("PORT", "8000"))

if not DEEPSEEK_API_KEY:
    raise RuntimeError("DEEPSEEK_API_KEY is not set. Check your .env file.")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

app = FastAPI(title="Steelman Counter-Argument Generator")


def extract_json(text: str):
    """Parse JSON from raw model output, handling markdown code blocks and extra text."""
    if text is None:
        return None

    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from ```json ... ``` block
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try extracting from first { to last }
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    return None


STEELMAN_SYSTEM_PROMPT = """You are a ruthless, intellectually honest debate adversary. Your job is to generate the STRONGEST possible counter-arguments against the user's claim.

Follow the steelman principle: do NOT attack a weak or distorted version of the argument. Instead, you must:
1. Fully understand the user's position in its most defensible form.
2. Construct the most devastating counter-arguments that would trouble even the original arguer.
3. Be precise. Cite concrete weaknesses, hidden assumptions, edge cases, empirical gaps, or logical flaws.

Output ONLY valid JSON with this exact structure:
{
  "restated_argument": "User's argument, rephrased in its strongest form (1-2 sentences)",
  "counterarguments": [
    {
      "title": "Short punchy title capturing the counter's essence (Korean or English, match user's language)",
      "content": "Detailed steelman counter-argument. Explain WHY this is hard to defend against. Be concrete and specific. (3-5 sentences)",
      "severity": 85
    }
  ],
  "average_severity": 78.3,
  "verdict": "Overall assessment. Is the original argument defensible? Summarize the key vulnerability in 2-3 sentences."
}

Rules:
- severity: 1-100 integer. Higher = harder to defend against.
  - 1-20: trivial, easily dismissed
  - 21-40: weak, has obvious rebuttals
  - 41-60: moderate, requires careful response
  - 61-80: strong, exposes real weakness
  - 81-100: devastating, may be fatal to the argument
- Generate EXACTLY 3 counterarguments.
- average_severity: arithmetic mean of the 3 severities.
- Write in the same language as the user's input."""

app.mount("/static", StaticFiles(directory="static"), name="static")


class ArgumentRequest(BaseModel):
    argument: str


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.post("/api/generate")
async def generate_counterarguments(req: ArgumentRequest):
    if not req.argument.strip():
        return JSONResponse({"error": "Argument cannot be empty"}, status_code=400)

    if len(req.argument) > 4000:
        return JSONResponse({"error": "Argument too long (max 4000 chars)"}, status_code=400)

    user_prompt = f"Generate steelman counter-arguments for this claim:\n\n{req.argument.strip()}"

    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": STEELMAN_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=4096,
        )

        if not response.choices:
            return JSONResponse({"error": "API returned no choices"}, status_code=500)

        raw = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason

        if raw is None:
            return JSONResponse({"error": "Empty response from API"}, status_code=500)

        if finish_reason == "length":
            return JSONResponse(
                {"error": f"Response truncated (token limit). Raw: {raw[:300]}..."},
                status_code=500,
            )

        result = extract_json(raw)
        if result is None:
            preview = raw[:500].replace("\n", "\\n")
            print(f"[ERROR] JSON parse failed. Finish: {finish_reason}. Raw ({len(raw)} chars):\n{raw[:2000]}", file=sys.stderr)
            return JSONResponse(
                {"error": f"Failed to parse API response as JSON. Raw preview: {preview}"},
                status_code=500,
            )

        required_keys = {"restated_argument", "counterarguments", "average_severity", "verdict"}
        if not required_keys.issubset(result.keys()):
            return JSONResponse({"error": "Invalid response structure from API"}, status_code=500)

        if len(result["counterarguments"]) != 3:
            return JSONResponse({"error": "Expected exactly 3 counterarguments"}, status_code=500)

        for ca in result["counterarguments"]:
            if not all(k in ca for k in ("title", "content", "severity")):
                return JSONResponse({"error": "Invalid counterargument structure"}, status_code=500)
            severity = ca["severity"]
            if not isinstance(severity, (int, float)) or not (1 <= severity <= 100):
                return JSONResponse({"error": f"Severity must be 1-100, got {severity}"}, status_code=500)

        return JSONResponse(result)

    except Exception as e:
        print(f"[ERROR] API call failed: {e}", file=sys.stderr)
        return JSONResponse({"error": str(e)}, status_code=500)


def main():
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=PORT, reload=True)


if __name__ == "__main__":
    main()
