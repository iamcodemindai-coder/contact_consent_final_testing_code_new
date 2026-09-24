import os
import json
import logging
import requests

from dotenv import load_dotenv
from urllib.parse import urlparse

from oauth_token_manager_2 import DatabricksTokenManager


logger = logging.getLogger(__name__)

load_dotenv()


# ============================================================
# CONFIGURATION
# ============================================================

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")


# ============================================================
# CREATE TOKEN MANAGER
# ============================================================

def create_token_manager():

    if not OPENAI_BASE_URL:
        raise RuntimeError(
            "OPENAI_BASE_URL is missing in .env"
        )

    if not CLIENT_ID:
        raise RuntimeError(
            "CLIENT_ID is missing in .env"
        )

    if not CLIENT_SECRET:
        raise RuntimeError(
            "CLIENT_SECRET is missing in .env"
        )

    parsed_url = urlparse(OPENAI_BASE_URL)

    host = (
        f"{parsed_url.scheme}://{parsed_url.netloc}"
    )

    return DatabricksTokenManager(
        host=host,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        model_name=OPENAI_MODEL or "UNKNOWN"
    )


token_manager = create_token_manager()


# ============================================================
# CONSENT PROMPT
# ============================================================

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


# ============================================================
# EMPTY RESULT
# ============================================================

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


# ============================================================
# PARSE JSON RESPONSE
# ============================================================

def parse_json_response(text):

    if not text:
        raise ValueError(
            "Model returned empty response"
        )

    text = text.strip()

    if text.startswith("```"):

        lines = text.splitlines()

        lines = [
            line
            for line in lines
            if not line.strip().startswith("```")
        ]

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

        raise ValueError(
            "No JSON object found in model response"
        )

    data = json.loads(
        text[start:end + 1]
    )

    if not isinstance(data, dict):

        raise ValueError(
            "Model response is not a JSON object"
        )

    return data


# ============================================================
# EXTRACT CONSENT
# ============================================================

def extract_consent(chatqna):

    logger.info("CONSENT AGENT STARTED")

    if chatqna is None:
        chatqna = ""

    if not isinstance(chatqna, str):
        chatqna = str(chatqna)

    if not chatqna.strip():

        logger.info(
            "Consent Agent received empty Chatqna"
        )

        return empty_result()

    try:

        # ----------------------------------------------------
        # GET CACHED / REFRESHED OAUTH TOKEN
        # ----------------------------------------------------

        access_token = token_manager.get_token()

        # ----------------------------------------------------
        # DATABRICKS CHAT COMPLETIONS URL
        # ----------------------------------------------------

        url = (
            f"{OPENAI_BASE_URL.rstrip('/')}"
            "/chat/completions"
        )

        # ----------------------------------------------------
        # HEADERS
        # ----------------------------------------------------

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # ----------------------------------------------------
        # REQUEST PAYLOAD
        # ----------------------------------------------------

        payload = {
            "model": OPENAI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": CONSENT_PROMPT
                },
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
        }

        logger.info(
            "Calling Databricks Chat Completions API"
        )

        # ----------------------------------------------------
        # API CALL
        # ----------------------------------------------------

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120
        )

        logger.info(
            "Consent Agent API response status=%s",
            response.status_code
        )

        # ----------------------------------------------------
        # HANDLE API ERROR
        # ----------------------------------------------------

        if response.status_code != 200:

            logger.error(
                "Consent Agent API request failed. status=%s",
                response.status_code
            )

            response.raise_for_status()

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        response_data = response.json()

        choices = response_data.get(
            "choices",
            []
        )

        if not choices:

            logger.error(
                "Consent Agent response contains no choices"
            )

            return empty_result()

        message = choices[0].get(
            "message",
            {}
        )

        content = message.get(
            "content",
            ""
        ) or ""

        logger.info(
            "Consent Agent response received"
        )

        # ----------------------------------------------------
        # PARSE RESULT
        # ----------------------------------------------------

        result = parse_json_response(content)

        result.setdefault(
            "Additional Fields",
            empty_result()["Additional Fields"]
        )

        result.setdefault(
            "Reported Verbatim",
            []
        )

        result.setdefault(
            "Consent Confidence Score",
            0
        )

        logger.info(
            "Consent Agent completed"
        )

        return result

    except Exception:

        logger.exception(
            "Consent Agent failed during LLM/API call"
        )

        return empty_result()