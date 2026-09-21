from typing import TypedDict, Dict, Any


class AgentState(TypedDict, total=False):
    input_data: Dict[str, Any]
    contact_result: Dict[str, Any]
    consent_result: Dict[str, Any]
    final_result: Dict[str, Any]
