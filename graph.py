import logging

from langgraph.graph import StateGraph, START, END

from state import AgentState
from supervisor import get_chatqna, create_final_output
from contact_agent import extract_contacts
from consent_agent import extract_consent

logger = logging.getLogger(__name__)


def supervisor_node(state: AgentState):
    """Prepare the input for both agents."""
    input_data = state.get("input_data", {})
    chatqna = get_chatqna(input_data)

    logger.info("Supervisor started")
    logger.info("Chatqna sent to BOTH agents. length=%d", len(chatqna))

    return {"input_data": input_data}


def contact_node(state: AgentState):
    """Run Contact Agent."""
    logger.info("========== CONTACT AGENT STARTED ==========")

    chatqna = get_chatqna(state.get("input_data", {}))
    result = extract_contacts(chatqna)

    logger.info(
        "========== CONTACT AGENT COMPLETED ==========: contacts=%d",
        len(result.get("chat_response", []))
        if isinstance(result.get("chat_response"), list)
        else 0
    )

    return {"contact_result": result}


def consent_node(state: AgentState):
    """Run Consent Agent."""
    logger.info("========== CONSENT AGENT STARTED ==========")

    chatqna = get_chatqna(state.get("input_data", {}))
    result = extract_consent(chatqna)

    logger.info("========== CONSENT AGENT COMPLETED ==========")

    return {"consent_result": result}


def final_supervisor_node(state: AgentState):
    """Join Contact and Consent results. No LLM is used here."""
    logger.info("Final Supervisor started")

    final_result = create_final_output(
        input_data=state.get("input_data", {}),
        contact_result=state.get("contact_result", {}),
        consent_result=state.get("consent_result", {})
    )

    logger.info("Final Supervisor completed")
    return {"final_result": final_result}


# Build graph.
builder = StateGraph(AgentState)

builder.add_node("supervisor", supervisor_node)
builder.add_node("contact", contact_node)
builder.add_node("consent", consent_node)
builder.add_node("final_supervisor", final_supervisor_node)

# Start -> Supervisor.
builder.add_edge(START, "supervisor")

# Supervisor -> Contact and Consent in parallel.
builder.add_edge("supervisor", "contact")
builder.add_edge("supervisor", "consent")

# Both agents -> Final Supervisor.
builder.add_edge("contact", "final_supervisor")
builder.add_edge("consent", "final_supervisor")

# Final Supervisor -> End.
builder.add_edge("final_supervisor", END)

graph = builder.compile()
