import os
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")

logger.info(
    "Consent Agent configuration: key_present=%s, base_url=%s, model=%s",
    bool(OPENAI_API_KEY),
    OPENAI_BASE_URL or "<default>",
    OPENAI_MODEL or "<missing>"
)

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL or None
)


CONSENT_PROMPT = """
You are a Consent Extraction Agent.

Read ONLY the supplied transcript and extract these five permissions:
1. Permission To Contact HCP
2. Permission To Contact Reporter
3. Permission To Contact Patient
4. Permission To Contact Complaint
5. Permission To Contact Via Text

Each value must be YES, NO, or UNKNOWN.
Never guess.
Phone consent does not mean text consent.
If the caller is the Patient, Permission To Contact Patient is normally UNKNOWN unless another patient is explicitly discussed.
Use the conversation meaning, including clear indirect answers.
Reported Verbatim must contain only the bot/user evidence used to determine consent.

Return JSON only in this exact structure:
{
  "Additional Fields": [
    {"Permission To Contact HCP": "UNKNOWN"},
    {"Permission To Contact Reporter": "UNKNOWN"},
    {"Permission To Contact Patient": "UNKNOWN"},
    {"Permission To Contact Complaint": "UNKNOWN"},
    {"Permission To Contact Via Text": "UNKNOWN"}
  ],
  "Reported Verbatim": [
    {"bot": "", "user": ""}
  ],
  "Consent Confidence Score": 0
}
"""


def empty_result():
    return {
        "Additional Fields": [
            {"Permission To Contact HCP": "UNKNOWN"},
            {"Permission To Contact Reporter": "UNKNOWN"},
            {"Permission To Contact Patient": "UNKNOWN"},
            {"Permission To Contact Complaint": "UNKNOWN"},
            {"Permission To Contact Via Text": "UNKNOWN"}
        ],
        "Reported Verbatim": [],
        "Consent Confidence Score": 0
    }


def parse_json_response(text):
    """Convert a model response into a Python dictionary."""
    if not text:
        raise ValueError("Model returned empty response")

    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response")

    data = json.loads(text[start:end + 1])

    if not isinstance(data, dict):
        raise ValueError("Model response is not a JSON object")

    return data


def extract_consent(chatqna):
    """Extract consent information from Chatqna."""
    logger.info("Consent Agent Started")

    if chatqna is None:
        chatqna = ""

    if not isinstance(chatqna, str):
        chatqna = str(chatqna)

    if not chatqna.strip():
        logger.info("Consent Agent received empty Chatqna")
        return empty_result()

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": CONSENT_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Extract consent from this transcript only.\n\n"
                        "TRANSCRIPT START\n"
                        + chatqna
                        + "\nTRANSCRIPT END"
                    )
                }
            ]
        )

        content = response.choices[0].message.content or ""
        logger.info("Consent Agent response length=%d", len(content))

        result = parse_json_response(content)

        result.setdefault("Additional Fields", empty_result()["Additional Fields"])
        result.setdefault("Reported Verbatim", [])
        result.setdefault("Consent Confidence Score", 0)

        logger.info("Consent Agent completed")
        return result

    except Exception:
        logger.exception("Consent Agent failed during LLM/API call")
        return empty_result()
