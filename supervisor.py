import logging

logger = logging.getLogger(__name__)

# Change only this value if the API field name changes later.
CHAT_FIELD = "Chatqna"


UNKNOWN_VALUES = {"", "unknown", "none", "null"}


def unknown(value):
    if value is None:
        return "Unknown"

    if isinstance(value, str) and value.strip().lower() in UNKNOWN_VALUES:
        return "Unknown"

    return value


def get_chatqna(input_data):
    """Read Chatqna. Lowercase chatqna is also supported."""
    if not isinstance(input_data, dict):
        return ""

    value = input_data.get(CHAT_FIELD)

    if value is None:
        value = input_data.get(CHAT_FIELD.lower(), "")

    if value is None:
        return ""

    return str(value)


def create_chat_response(contact_result):
    contacts = contact_result.get("chat_response", [])

    if not isinstance(contacts, list):
        return []

    final_contacts = []

    for contact in contacts:
        if not isinstance(contact, dict):
            continue

        final_contacts.append({
            "contact_type": unknown(contact.get("contact_type")),
            "contact_role": unknown(contact.get("contact_role")),
            "first_name": unknown(contact.get("first_name")),
            "last_name": unknown(contact.get("last_name")),
            "phone_number": unknown(contact.get("phone_number")),
            "additional_phone_number": unknown(contact.get("additional_phone_number")),
            "email_address": unknown(contact.get("email_address")),
            "date_of_birth": unknown(contact.get("date_of_birth")),
            "gender": unknown(contact.get("gender")),
            "address": unknown(contact.get("address")),
            "street": unknown(contact.get("street")),
            "city": unknown(contact.get("city")),
            "zip_postal_code": unknown(contact.get("zip_postal_code")),
            "state_province": unknown(contact.get("state_province")),
            "country": unknown(contact.get("country"))
        })

    return final_contacts


def normalize_consent_value(value):
    if value is None:
        return "Unknown"

    if isinstance(value, bool):
        return "Yes" if value else "No"

    value = str(value).strip().upper()

    if value == "YES":
        return "Yes"
    if value == "NO":
        return "No"
    if value in {"", "UNKNOWN", "NONE", "NULL"}:
        return "Unknown"

    return "Unknown"


def create_additional_fields(consent_result):
    fields = consent_result.get("Additional Fields", [])
    values = {}

    if isinstance(fields, list):
        for item in fields:
            if not isinstance(item, dict):
                continue

            for key, value in item.items():
                values[key.strip().lower()] = value

    return {
        "permission_to_contact_complaint": normalize_consent_value(
            values.get("permission to contact complaint")
        ),
        "permission_to_contact_hcp": normalize_consent_value(
            values.get("permission to contact hcp")
        ),
        "permission_to_contact_patient": normalize_consent_value(
            values.get("permission to contact patient")
        ),
        "permission_to_contact_reporter": normalize_consent_value(
            values.get("permission to contact reporter")
        ),
        "permission_to_contact_reporter_via_text": normalize_consent_value(
            values.get("permission to contact via text")
        )
    }


def format_verbatim(value):
    if not isinstance(value, list):
        return []

    result = []

    for item in value:
        if not isinstance(item, dict):
            continue

        bot = item.get("bot", "")
        user = item.get("user", "")

        if bot or user:
            result.append({"bot": bot, "user": user})

    return result


def combine_verbatim(contact_result, consent_result):
    contact = format_verbatim(contact_result.get("reported_verbatim", []))
    consent = format_verbatim(consent_result.get("Reported Verbatim", []))
    return contact + consent


def to_number(value):
    try:
        return float(str(value).replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def calculate_confidence(contact_result, consent_result):
    scores = []

    contact_score = to_number(
        contact_result.get("contact_confidence_score")
    )
    consent_score = to_number(
        consent_result.get("Consent Confidence Score")
    )

    if contact_score is not None:
        scores.append(contact_score)

    if consent_score is not None:
        scores.append(consent_score)

    if not scores:
        return 0

    return round(sum(scores) / len(scores), 2)


def create_final_output(input_data, contact_result, consent_result):
    """Create the fixed API response. No LLM is used here."""
    input_data = input_data if isinstance(input_data, dict) else {}
    contact_result = contact_result if isinstance(contact_result, dict) else {}
    consent_result = consent_result if isinstance(consent_result, dict) else {}

    output = {
        "MasterCaseId": input_data.get("MasterCaseId", ""),
        "AutomationReportId": input_data.get("AutomationReportId", ""),
        "Confidence": calculate_confidence(contact_result, consent_result),
        "Reported Verbatim": combine_verbatim(contact_result, consent_result),
        "ChatResponse": create_chat_response(contact_result),
        "Additional Fields": create_additional_fields(consent_result)
    }

    logger.info(
        "Final output created: MasterCaseId=%s, AutomationReportId=%s",
        output["MasterCaseId"],
        output["AutomationReportId"]
    )

    return output
