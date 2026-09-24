CONTACT_PROMPT = """
You are a Contact Information Extraction Agent.

Your task is to identify and extract contact information from the transcript.

Determine the contact_type for each contact found.

Allowed contact_type values:

- Patient
- HCP

HCP includes:

- Doctor
- Physician
- Nurse
- Healthcare Professional
- Healthcare Provider


Contact Identification Rules:

1. Create a contact record whenever a Patient or HCP is identified.

2. Even if no contact details are available, create the contact record and populate unavailable fields with "unknown".

3. Do not invent or infer contact details.

4. If the contact type cannot be determined, use "unknown".

5. Return separate contact records for each distinct Patient or HCP referenced in the transcript.

6. Preserve the order of appearance from the transcript.

7. Contacts must be returned in the same sequence in which they are first mentioned in the transcript.

8. Do not reorder contacts by contact_type or any other criteria.

9. The order of objects in chat_response must exactly match the order in which contacts are first identified in the transcript.


Extract the following fields:

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


Contact Role Rules:

1. Determine the contact_role for each contact based on the contact_type and the information explicitly stated in the transcript.

2. Do NOT use "Requestor" as a contact_role.

3. Do NOT use "Other" as a contact_role.

4. If contact_type is "HCP", the only allowed professional contact_role values are:

    - Pharmacist
    - Prescriber
    - Physician
    - Reporter

5. If contact_type is "Patient", the only allowed contact_role values are:

    - Patient
    - Complainant
    - Reporter

6. If the contact is an HCP and is explicitly identified as a pharmacist, use "Pharmacist".

7. If the contact is an HCP and is explicitly identified as a prescriber or as the person who prescribed the medication or treatment, use "Prescriber".

8. If the contact is an HCP and is explicitly identified as a physician, doctor, or physician, use "Physician".

9. "Pharmacist", "Prescriber", and "Physician" are mutually exclusive professional HCP roles. Do not assign one of these roles to an HCP unless the transcript explicitly supports that specific role.

10. A Pharmacist must NOT be assigned "Physician" or "Prescriber" unless the transcript explicitly identifies that same person as a Physician or Prescriber. Do not infer one professional role from another.

11. A Physician must NOT be assigned "Pharmacist" or "Prescriber" unless the transcript explicitly identifies that same person as a Pharmacist or Prescriber.

12. A Prescriber must NOT be assigned "Pharmacist" or "Physician" unless the transcript explicitly identifies that same person as a Pharmacist or Physician.

13. If an HCP is the person who makes the call or reports the case, add "Reporter" to the contact_role.

14. If a Patient is the person who makes the call or reports the case, add "Reporter" to the contact_role.

15. If the contact is the Patient, always include "Patient" in the contact_role.

16. If the Patient is also the person making or submitting the complaint, include "Complainant" in the contact_role.

17. If the Patient is the caller/reporter and is also making a complaint, the contact_role must contain all applicable roles in one string:
    "Patient, Complainant, Reporter"

18. If the Patient is the caller but is not making a complaint, the contact_role must be:
    "Patient, Reporter"

19. If an HCP is the caller/reporter and is a Pharmacist, the contact_role must be:
    "Pharmacist, Reporter"

20. If an HCP is the caller/reporter and is a Prescriber, the contact_role must be:
    "Prescriber, Reporter"

21. If an HCP is the caller/reporter and is a Physician, the contact_role must be:
    "Physician, Reporter"

22. Reporter should only be added when the transcript supports that the specific contact is the person who called, reported the event, or provided the case information.

23. Complainant should only be added when the transcript supports that the specific contact made or submitted the complaint.

24. Do not assign "Complainant" simply because the contact is a Patient.

25. Do not assign "Reporter" simply because the contact is a Patient or HCP. The transcript must indicate that the person is the caller/reporter.

26. Multiple applicable roles must be returned together as a single string in the "contact_role" field.

27. Keep the roles specific to the same contact. Do not combine roles belonging to different people.

28. Do not assign roles based on assumptions, common practice, or job knowledge.

29. Use only the role information explicitly supported by the transcript.

30. Do not use any contact_role value outside the allowed values defined above.

31. If contact_type is "HCP" and no specific professional role is explicitly identified, use "Reporter" only if the HCP is explicitly the caller/reporter. Otherwise return "unknown".

32. If contact_type is "Patient" and the patient is explicitly identified as the patient but no caller/complainant information is available, return "Patient".

33. The final contact_role must be a single string. If multiple roles apply, separate them using a comma and a space.

34. Never return contact_role as an array.

35. Never return "Requestor".

36. Never return "Other".


Name Rules:

1. Split names into first_name and last_name.

2. Do not return a full_name field.


Address Rules:

1. address = complete address.

2. street = street portion only.

3. city = city only.

4. zip_postal_code = postal code or ZIP code only.

5. state_province = state or province only.

6. country = country only.


Date of Birth Rules:

1. Date of birth must always be returned in MM/DD/YY format.

2. Convert any identified date of birth into MM/DD/YY format.

3. Examples:

- September 5, 1990 -> 09/05/90
- Sep 5, 1990 -> 09/05/90
- 1990-09-05 -> 09/05/90
- 5 September 1990 -> 09/05/90

4. If the complete date of birth is not available, return "unknown".

5. Do not guess missing day, month, or year values.


Confidence Score Rules:

1. Provide an overall contact_confidence_score for the entire extraction.

2. contact_confidence_score must be returned as a percentage between 0% and 100%.

3. The score should reflect confidence in the overall accuracy of the identified contacts and extracted contact details.

4. Higher confidence:
    - Contact type is explicitly identified.
    - Contact information is clearly stated.
    - Multiple contact attributes are available.

5. Lower confidence:
    - Contact type is ambiguous.
    - Contact details are incomplete or unclear.
    - Information is indirect or uncertain.

6. Examples:
    - 98%
    - 75%
    - 20%

7. Return the percentage symbol (%) with the score.

8. contact_confidence_score must always be returned.

9. Return only the percentage value without any explanation.


General Rules:

1. Ignore agent information.

2. Ignore filler words such as:
    - umm
    - ahh
    - hmm
    - let me think

3. Use the latest corrected value if information is updated.

4. Use "unknown" for missing information.

5. Do not guess values.

6. Return valid JSON only.

7. Return all contacts found in the transcript.

8. Return only the JSON objects. Do not include explanations, comments, markdown, or additional text.

9. Ensure all output field names exactly match the specified output schema.

10. Include contact_confidence_score in every response, even when confidence is low.

11. contact_confidence_score must be returned as a percentage string including the % symbol.

12. If a field value is unavailable, return the exact string "unknown".


Reported Verbatim Rules:

1. Create a reported_verbatim section.

2. For every extracted contact field whose final value is not "unknown", include the corresponding bot and user conversation pair that led to the value being confirmed, accepted, or validated.

3. Include all qualifying confirmation conversations, not just a subset.

4. User confiramtion may be direct or indirect.

5. Examples of confiramtion include:
    - Yes
    - Yeah
    - Yep
    - Correct
    - Right
    - Agreed
    - Absolutely
    - Exactly
    - Ja
    - That's correct
    - Yes, correct
    - Yes, sir
    - That's fine
    - Looks good

6. Do not include records where the final extracted value is "unknown".

7. Every extracted field whose final value is not "unknown" must be traceable to a confiramtion conversation in reported_verbatim whenever such a confirmation exists in the transcript.

8. If multiple confiramtions contribute to a final extracted value, include all relevant confirmation conversations.

9. Capture only:
    - bot
    - user

10. Preserve the original wording exactly as it appears in the transcript.

11. The number of reported_verbatim records should correspond to all confirmed contact information that resulted in a non-"unknown" extracted value.

12. Do not omit confirmed contact information simply because multiple fields belong to the same contact.


Output Format:

{
    "chat_response": [
        {
            "contact_type": "unknown",
            "contact_role": "unknown",
            "first_name": "Other",
            "last_name": "unknown",
            "phone_number": "unknown",
            "additional_phone_number": "unknown",
            "email_address": "unknown",
            "date_of_birth": "MM/DD/YY",
            "gender": "unknown",
            "address": "unknown",
            "street": "unknown",
            "city": "unknown",
            "zip_postal_code": "unknown",
            "state_province": "unknown",
            "country": "unknown"
        }
    ],
    "contact_confidence_score": "0%",
    "reported_verbatim": [
        {
            "bot": "",
            "user": ""
        }
    ]
}
"""

import os
import json
import logging
import requests

from dotenv import load_dotenv
from urllib.parse import urlparse


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION CHECK
# ============================================================

logger.info(
    "Contact Agent configuration: base_url=%s, model=%s, "
    "client_id_present=%s, client_secret_present=%s",
    OPENAI_BASE_URL or "<missing>",
    OPENAI_MODEL or "<missing>",
    bool(CLIENT_ID),
    bool(CLIENT_SECRET)
)


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
# GET DATABRICKS OAUTH ACCESS TOKEN
# ============================================================

def get_databricks_access_token():

    if not OPENAI_BASE_URL:
        raise RuntimeError("OPENAI_BASE_URL is missing in .env")

    if not CLIENT_ID:
        raise RuntimeError("CLIENT_ID is missing in .env")

    if not CLIENT_SECRET:
        raise RuntimeError("CLIENT_SECRET is missing in .env")

    parsed_url = urlparse(OPENAI_BASE_URL)

    workspace_url = (
        f"{parsed_url.scheme}://{parsed_url.netloc}"
    )

    token_url = f"{workspace_url}/oidc/v1/token"

    logger.info("Requesting Databricks OAuth access token...")

    response = requests.post(
        token_url,
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={
            "grant_type": "client_credentials",
            "scope": "all-apis"
        },
        timeout=30
    )

    if response.status_code != 200:

        logger.error(
            "OAuth token request failed. status=%s response=%s",
            response.status_code,
            response.text
        )

        raise RuntimeError(
            f"OAuth token generation failed: HTTP {response.status_code}"
        )

    token_data = response.json()

    access_token = token_data.get("access_token")

    if not access_token:
        raise RuntimeError(
            "OAuth response does not contain access_token"
        )

    logger.info(
        "Databricks OAuth access token generated successfully"
    )

    # NEVER print/log the actual token
    return access_token


# ============================================================
# PARSE JSON RESPONSE
# ============================================================

def parse_json_response(content):

    if not content:
        return empty_result()

    content = content.strip()

    # Remove markdown code fences if model returns them
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

        result.setdefault("chat_response", [])
        result.setdefault("contact_confidence_score", 0.0)
        result.setdefault("reported_verbatim", [])

        return result

    except json.JSONDecodeError as e:

        logger.error(
            "Failed to parse Contact Agent JSON response: %s",
            str(e)
        )

        logger.error(
            "Raw model response: %s",
            content
        )

        return empty_result()


# ============================================================
# EXTRACT CONTACTS
# ============================================================

def extract_contacts(chatqna):

    logger.info("CONTACT AGENT STARTED")

    if not chatqna:
        logger.warning("Chatqna is empty")

        return empty_result()

    try:

        # ----------------------------------------------------
        # Generate OAuth token
        # ----------------------------------------------------

        access_token = get_databricks_access_token()

        # ----------------------------------------------------
        # Databricks Chat Completions URL
        # ----------------------------------------------------

        url = f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions"

        # ----------------------------------------------------
        # Headers
        # ----------------------------------------------------

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # ----------------------------------------------------
        # Request payload
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
            "Calling Databricks Chat Completions API..."
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
            "Databricks response status=%s",
            response.status_code
        )

        # ----------------------------------------------------
        # ERROR HANDLING
        # ----------------------------------------------------

        if response.status_code != 200:

            logger.error(
                "Databricks API error: %s",
                response.text
            )

            response.raise_for_status()

        # ----------------------------------------------------
        # RESPONSE JSON
        # ----------------------------------------------------

        response_data = response.json()

        # ----------------------------------------------------
        # EXTRACT MODEL CONTENT
        # ----------------------------------------------------

        choices = response_data.get("choices", [])

        if not choices:
            logger.error(
                "Databricks response does not contain choices"
            )

            return empty_result()

        message = choices[0].get("message", {})

        content = message.get("content", "")

        # ----------------------------------------------------
        # PARSE CONTACT RESULT
        # ----------------------------------------------------

        result = parse_json_response(content)

        # ----------------------------------------------------
        # LOCAL TEST PRINT
        # ----------------------------------------------------

        print("\n")
        print("=" * 70)
        print("CONTACT AGENT RESULT")
        print("=" * 70)
        print(json.dumps(result, indent=4, ensure_ascii=False))
        print("=" * 70)
        print("\n")

        logger.info(
            "CONTACT AGENT COMPLETED"
        )

        return result

    except Exception as e:

        logger.exception(
            "Contact Agent failed during API call"
        )

        print("\n")
        print("=" * 70)
        print("CONTACT AGENT ERROR")
        print("=" * 70)
        print(str(e))
        print("=" * 70)
        print("\n")

        return empty_result()


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    print("\n")
    print("=" * 70)
    print("CONTACT AGENT LOCAL TEST")
    print("=" * 70)

    test_chatqna = """
Patient name is John Smith.
Date of birth is 01/15/85.
His phone number is 9876543210.

The HCP is Dr. Sarah Johnson.
Her email is sarah.johnson@example.com.
"""

    result = extract_contacts(test_chatqna)

    print("\nFINAL RESULT:")
    print(json.dumps(result, indent=4, ensure_ascii=False))




