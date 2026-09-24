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
# CONTACT AGENT PROMPT
# ============================================================

CONTACT_AGENT_PROMPT = """
You are a Contact Information Extraction Agent.

Your task is to extract all relevant Patient and HCP contact
information from the provided Chatqna transcript.

Rules:

1. Identify every distinct Patient and HCP mentioned in the conversation.
2. Keep contacts in their first appearance order.
3. If a value is corrected later in the conversation, use the latest
   corrected value.
4. Do not invent information.
5. If a field is not available, use "Unknown".
6. Date of Birth should be returned in MM/DD/YY format whenever available.
7. Extract only information that is explicitly present in the transcript.
8. Keep the response strictly in JSON format.

Return the following structure:

{
    "chat_response": [
        {
            "contact_type": "Patient or HCP",
            "contact_role": "Patient or HCP",
            "first_name": "value",
            "last_name": "value",
            "date_of_birth": "MM/DD/YY or Unknown",
            "phone_number": "value or Unknown",
            "email": "value or Unknown",
            "address": "value or Unknown"
        }
    ],
    "contact_confidence_score": 0.0,
    "reported_verbatim": []
}

Confidence score should be between 0 and 1.

reported_verbatim should contain relevant exact statements from
the conversation that support the extracted contact information.
"""


# ============================================================
# EMPTY RESULT
# ============================================================

def empty_result():

    return {
        "chat_response": [],
        "contact_confidence_score": 0.0,
        "reported_verbatim": []
    }


# ============================================================
# PARSE JSON RESPONSE
# ============================================================

def parse_json_response(content):

    if not content:
        return empty_result()

    content = content.strip()

    if content.startswith("```json"):
        content = content[7:]

    elif content.startswith("```"):
        content = content[3:]

    if content.endswith("```"):
        content = content[:-3]

    content = content.strip()

    try:

        result = json.loads(content)

        if not isinstance(result, dict):
            return empty_result()

        result.setdefault(
            "chat_response",
            []
        )

        result.setdefault(
            "contact_confidence_score",
            0.0
        )

        result.setdefault(
            "reported_verbatim",
            []
        )

        return result

    except json.JSONDecodeError:

        logger.error(
            "Failed to parse Contact Agent response as JSON"
        )

        return empty_result()


# ============================================================
# EXTRACT CONTACTS
# ============================================================

def extract_contacts(chatqna):

    logger.info("CONTACT AGENT STARTED")

    if chatqna is None:
        chatqna = ""

    if not isinstance(chatqna, str):
        chatqna = str(chatqna)

    if not chatqna.strip():

        logger.info(
            "Contact Agent received empty Chatqna"
        )

        return empty_result()

    try:

        # ----------------------------------------------------
        # GET CACHED / REFRESHED OAUTH TOKEN
        # ----------------------------------------------------

        access_token = token_manager.get_token()

        # ----------------------------------------------------
        # DATabricks CHAT COMPLETIONS URL
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
                    "content": CONTACT_AGENT_PROMPT
                },
                {
                    "role": "user",
                    "content": chatqna
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
            "Contact Agent API response status=%s",
            response.status_code
        )

        # ----------------------------------------------------
        # HANDLE API ERROR
        # ----------------------------------------------------

        if response.status_code != 200:

            logger.error(
                "Contact Agent API request failed. status=%s",
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
                "Contact Agent response contains no choices"
            )

            return empty_result()

        message = choices[0].get(
            "message",
            {}
        )

        content = message.get(
            "content",
            ""
        )

        # ----------------------------------------------------
        # PARSE RESULT
        # ----------------------------------------------------

        result = parse_json_response(content)

        logger.info(
            "Contact Agent completed"
        )

        return result

    except Exception:

        logger.exception(
            "Contact Agent failed during LLM/API call"
        )

        return empty_result()