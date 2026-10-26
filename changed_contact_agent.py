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
# TOKEN MANAGER
# ============================================================

def create_token_manager():

    if not OPENAI_BASE_URL:
        raise RuntimeError("OPENAI_BASE_URL is missing in .env")

    if not CLIENT_ID:
        raise RuntimeError("CLIENT_ID is missing in .env")

    if not CLIENT_SECRET:
        raise RuntimeError("CLIENT_SECRET is missing in .env")

    parsed_url = urlparse(OPENAI_BASE_URL)
    host = f"{parsed_url.scheme}://{parsed_url.netloc}"

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

CONTACT_PROMPT = """
You are a Contact Information Extraction Agent.

INPUT:
The user message contains a JSON object with:
- MasterCaseId
- Notes
- chatqna
- AutomationReportId

Extract contact information from BOTH chatqna and Notes.

SOURCE RULES:
1. Chatqna is a bot/user conversation transcript.
2. Notes is plain text and may contain contact information.
3. Extract information from either source, even if the other source is empty.
4. Identify every distinct Patient, HCP, and Other HCP.
5. Do not merge different people into one contact.
6. Preserve the order in which contacts are first identified in chatqna,
   followed by contacts found only in Notes.
7. Do not guess or invent information.

CONTACT TYPES:
- Patient
- HCP
- Other HCP

HCP includes doctors, physicians, nurses, healthcare professionals,
and healthcare providers.

Other HCP includes spouses, family members, caregivers, guardians,
friends, relatives, and representatives communicating on behalf of
a patient, unless they are explicitly identified as a Patient or HCP.

CONTACT FIELDS:
- contact_type
- contact_role
- first_name
- last_name
- phone_number
- additional_phone_number
- email_address
- date_of_birth
- gender
- address
- street
- city
- zip_postal_code
- state_province
- country

MISSING VALUES:
1. If a field is not available from either source, return JSON null.
2. Do not return the string "unknown" for missing contact fields.
3. Do not guess missing values.
4. Convert dates of birth to MM/DD/YY when the complete date is available.

CONTACT ROLE RULES:
1. Never use Requestor or Other as a contact_role.
2. Patient roles may include Patient, Complainant, and Reporter.
3. HCP roles may include Pharmacist, Prescriber, Physician, and Reporter.
4. Other HCP may only have the Reporter role.
5. Assign roles only when explicitly supported by the source.
6. Multiple applicable roles must be returned as one comma-separated string.
7. Do not combine roles belonging to different people.
8. A Patient must include Patient in contact_role.
9. Add Complainant only when the person explicitly makes or submits a complaint.
10. Add Reporter only when the person is explicitly the caller, reporter,
    or source of case information.
11. Do not infer professional roles from job knowledge.

NAME RULES:
1. Split names into first_name and last_name.
2. Do not return a full_name field.
3. Use the latest corrected value within the same source when a correction
   is explicitly confirmed.
4. Do not silently resolve conflicts between Chatqna and Notes.

EMAIL RULES:
1. Preserve a complete literal email address exactly as provided.
2. Resolve a placeholder such as mylastname@gmail.com only when the
   corresponding name is explicitly available for the same contact.
3. Never guess an email address.

ADDRESS RULES:
- address: complete address
- street: street portion
- city: city
- zip_postal_code: ZIP or postal code
- state_province: state or province
- country: country

CONFLICT RULES:
1. Compare each field from chatqna and Notes for the same contact.
2. If both sources provide the same value, return the value normally.
3. If only one source provides a value, return that value normally.
4. If neither source provides a value, return null.
5. If both sources explicitly provide different values for the same field
   and same contact, return a conflict object.
6. Do not create conflicts for mere formatting differences that represent
   the same value.
7. Never silently choose one source's value when a genuine conflict exists.

A conflict field must use this structure:
{
  "status": "conflict",
  "candidates": [
    {
      "<field_name>": "<value from chatqna>",
      "source": "chatqna",
      "verbatim": [
        {
          "bot": "<exact bot text>",
          "user": "<exact user text>"
        }
      ]
    },
    {
      "<field_name>": "<value from notes>",
      "source": "notes",
      "verbatim": ["<exact relevant notes text>"]
    }
  ]
}

REPORTED VERBATIM RULES:
1. Organize verbatim evidence by contact, not by individual field.
2. For Chatqna, preserve exact relevant bot/user conversation pairs.
3. Include relevant confirmation exchanges when available.
4. For Notes, return exact relevant text strings.
5. Notes must not be fabricated into bot/user dialogue.
6. Do not include empty placeholder evidence.
7. In source-summary objects, use:
   - Reported_verbatim_Patient for Patient
   - Reported_verbatim_HCP for HCP
   - Reported_verbatim_Other HCP for Other HCP
8. Include a source-summary object only when that source contains relevant
   evidence for that contact.
9. For a conflict candidate, include the evidence from that candidate's source.
10. Do not attach evidence to an unrelated contact.

OUTPUT FORMAT:
Return valid JSON only. Do not use Markdown fences or explanations.

The output must contain exactly these top-level keys:
{
  "MasterCaseId": "",
  "AutomationReportId": "",
  "Confidence": 0.0,
  "ChatResponse": []
}

MasterCaseId and AutomationReportId are metadata.
Do not generate or modify these IDs. The application will preserve their
original input values.

Confidence must be a numeric value between 0 and 100.

ChatResponse must be one array. For each contact:
1. Include the relevant chatqna source-summary object, if applicable.
2. Include the relevant notes source-summary object, if applicable.
3. Include one contact-data object with the contact fields.

For missing contact fields, use JSON null.
For conflicting fields, use the conflict object structure above.
If both sources are empty, the application will return an empty ChatResponse.

Return only valid JSON.
"""


# ============================================================
# EMPTY RESULT
# ============================================================

def empty_result(master_case_id="", automation_report_id=""):

    return {
        "MasterCaseId": master_case_id,
        "AutomationReportId": automation_report_id,
        "Confidence": 0.0,
        "ChatResponse": []
    }


# ============================================================
# PARSE JSON RESPONSE
# ============================================================

def parse_json_response(content, master_case_id="", automation_report_id=""):

    if not content:
        return empty_result(master_case_id, automation_report_id)

    content = content.strip()

    if content.startswith("```json"):
        content = content[len("```json"):].strip()

    elif content.startswith("```"):
        content = content[len("```"):].strip()

    if content.endswith("```"):
        content = content[:-3].strip()

    try:

        result = json.loads(content)

        if not isinstance(result, dict):
            return empty_result(master_case_id, automation_report_id)

        result.setdefault("Confidence", 0.0)
        result.setdefault("ChatResponse", [])

        if not isinstance(result["ChatResponse"], list):
            return empty_result(master_case_id, automation_report_id)

        # Preserve IDs from input, not from the LLM response.
        result["MasterCaseId"] = master_case_id
        result["AutomationReportId"] = automation_report_id

        return result

    except json.JSONDecodeError:

        logger.exception("Failed to parse Contact Agent response as JSON")

        return empty_result(master_case_id, automation_report_id)


# ============================================================
# EXTRACT CONTACTS
# ============================================================

def extract_contacts(chatqna=None, notes=None):

    logger.info("CONTACT AGENT STARTED")

    master_case_id = ""
    automation_report_id = ""

    # --------------------------------------------------------
    # SUPPORT COMPLETE INPUT JSON
    # --------------------------------------------------------

    if isinstance(chatqna, dict):

        input_data = chatqna

        master_case_id = input_data.get("MasterCaseId", "")
        automation_report_id = input_data.get("AutomationReportId", "")

        chatqna = input_data.get("chatqna", "")
        notes = input_data.get("Notes", "")

    # --------------------------------------------------------
    # NORMALIZE INPUTS
    # --------------------------------------------------------

    if chatqna is None:
        chatqna = ""

    if notes is None:
        notes = ""

    if not isinstance(chatqna, str):
        chatqna = str(chatqna)

    if not isinstance(notes, str):
        notes = str(notes)

    # --------------------------------------------------------
    # BOTH SOURCES EMPTY
    # --------------------------------------------------------

    if not chatqna.strip() and not notes.strip():

        logger.info("Chatqna and Notes are both empty")

        return empty_result(
            master_case_id,
            automation_report_id
        )

    # --------------------------------------------------------
    # PREPARE INPUT FOR LLM
    # --------------------------------------------------------

    source_input = json.dumps(
        {
            "chatqna": chatqna,
            "notes": notes
        },
        ensure_ascii=False
    )

    try:

        # ----------------------------------------------------
        # GET ACCESS TOKEN
        # ----------------------------------------------------

        access_token = token_manager.get_token()

        # ----------------------------------------------------
        # API URL
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
        # PAYLOAD
        # ----------------------------------------------------

        payload = {
            "model": OPENAI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": CONTACT_PROMPT
                },
                {
                    "role": "user",
                    "content": source_input
                }
            ]
        }

        logger.info("Calling Databricks Chat Completions API")

        # ----------------------------------------------------
        # API REQUEST
        # ----------------------------------------------------

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120
        )

        logger.info(
            "Contact Agent API response status = %s",
            response.status_code
        )

        response.raise_for_status()

        # ----------------------------------------------------
        # READ API RESPONSE
        # ----------------------------------------------------

        response_data = response.json()

        choices = response_data.get("choices", [])

        if not choices:

            logger.error("Contact Agent response contains no choices")

            return empty_result(
                master_case_id,
                automation_report_id
            )

        message = choices[0].get("message", {})

        content = message.get("content", "")

        # ----------------------------------------------------
        # PARSE FINAL RESPONSE
        # ----------------------------------------------------

        result = parse_json_response(
            content,
            master_case_id,
            automation_report_id
        )

        logger.info("Contact Agent completed")

        return result

    except Exception:

        logger.exception("Contact Agent failed during LLM/API call")

        return empty_result(
            master_case_id,
            automation_report_id
        )