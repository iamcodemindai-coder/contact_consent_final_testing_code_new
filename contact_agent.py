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
    "Contact Agent configuration: key_present=%s, base_url=%s, model=%s",
    bool(OPENAI_API_KEY),
    OPENAI_BASE_URL or "<default>",
    OPENAI_MODEL or "<missing>"
)

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL or None
)


CONTACT_PROMPT = """
You are a Contact Information Extraction Agent.

Read ONLY the supplied transcript and extract every distinct Patient or HCP.
Keep contacts in the order they first appear.
Never guess. Missing values must be "unknown".
Use the latest corrected value when the transcript corrects earlier information.
Date of birth must be MM/DD/YY.

Return JSON only in this exact structure:
{
  "chat_response": [
    {
      "contact_type": "Patient/HCP/unknown",
      "contact_role": "Pharmacist/Prescriber/Requestor/Complainant/Patient/Physician/Reporter/Other/unknown",
      "first_name": "",
      "last_name": "",
      "phone_number": "",
      "additional_phone_number": "",
      "email_address": "",
      "date_of_birth": "",
      "gender": "",
      "address": "",
      "street": "",
      "city": "",
      "zip_postal_code": "",
      "state_province": "",
      "country": ""
    }
  ],
  "contact_confidence_score": "0%",
  "reported_verbatim": [
    {"bot": "", "user": ""}
  ]
}

Rules:
- Extract only facts stated in the transcript.
- Do not create a contact from the bot's own identity.
- Keep Patient and HCP as separate contacts when both are mentioned.
- reported_verbatim must contain only transcript evidence used for contact extraction.
- If no contact is found, chat_response must be [].
"""


def empty_result():
    return {
        "chat_response": [],
        "contact_confidence_score": "0%",
        "reported_verbatim": []
    }


def parse_json_response(text):
    """Convert a model response into a Python dictionary."""
    if not text:
        raise ValueError("Model returned empty response")

    text = text.strip()

    # Remove markdown code fences if the model adds them.
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # First try the complete response.
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # If the model added text around the JSON, take the JSON object only.
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response")

    data = json.loads(text[start:end + 1])

    if not isinstance(data, dict):
        raise ValueError("Model response is not a JSON object")

    return data


def extract_contacts(chatqna):
    """Extract contact information from Chatqna."""
    logger.info("Contact Agent Started")

    if chatqna is None:
        chatqna = ""

    if not isinstance(chatqna, str):
        chatqna = str(chatqna)

    if not chatqna.strip():
        logger.info("Contact Agent received empty Chatqna")
        return empty_result()

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": CONTACT_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Extract contacts from this transcript only.\n\n"
                        "TRANSCRIPT START\n"
                        + chatqna
                        + "\nTRANSCRIPT END"
                    )
                }
            ]
        )

        content = response.choices[0].message.content or ""
        logger.info("Contact Agent response length=%d", len(content))

        result = parse_json_response(content)

        result.setdefault("chat_response", [])
        result.setdefault("contact_confidence_score", "0%")
        result.setdefault("reported_verbatim", [])

        logger.info(
            "Contact Agent completed. contacts=%d",
            len(result.get("chat_response", []))
            if isinstance(result.get("chat_response"), list)
            else 0
        )

        return result

    except Exception:
        logger.exception("Contact Agent failed during LLM/API call")
        return empty_result()
