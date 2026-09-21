# Contact + Consent LangGraph POC

## Flow

API Request
    -> Supervisor
    -> Contact Agent + Consent Agent (parallel)
    -> Final Supervisor
    -> Fixed JSON Output

The Final Supervisor does not call an LLM. It only combines the two agent results.

## Configuration

Create a `.env` file:

```text
OPENAI_API_KEY=your_client_key
OPENAI_BASE_URL=https://your-client-endpoint/v1
OPENAI_MODEL=your-model-name
```

The code does not set `temperature` and does not use provider-specific settings.

## Install

```bash
pip install -r requirements.txt
```

## Local test

Put the test request in `input.json`, then run:

```bash
python test.py
```

Output is saved to `output.json`.

## Run API

```bash
python main.py
```

Endpoint:

```text
POST /ccai
```

## Logs

Logs are written to:

```text
logs/contact_consent.log
```

## Important

- AIPC is removed.
- Contact and Consent always receive Chatqna.
- Contact and Consent run as parallel branches.
- Final Supervisor joins both branches.
- MasterCaseId and AutomationReportId are copied directly from input.
- `Chatqna` is supported, and lowercase `chatqna` is also accepted for testing.
- Missing contact values become `Unknown`.
- Missing consent values become `Unknown`.
