import os
import json
import uuid
import tempfile
import streamlit as st
from google.cloud import dialogflow
from google.api_core.client_options import ClientOptions

# --------------------------------
# CONFIG
# --------------------------------
PROJECT_ID = "solopool-mvp-xapu"
LANGUAGE_CODE = "en"

# --------------------------------
# FIX GOOGLE_APPLICATION_CREDENTIALS
# --------------------------------
# If Streamlit secret contains JSON instead of a file path,
# write it to a temp file and update the env var.
if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
    cred_value = os.environ["GOOGLE_APPLICATION_CREDENTIALS"].strip()

    # Detect JSON (starts with { )
    if cred_value.startswith("{"):
        creds_dict = json.loads(cred_value)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmp.write(json.dumps(creds_dict).encode("utf-8"))
        tmp.close()

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name

# --------------------------------
# SESSION ID (PERSISTENT)
# --------------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

SESSION_ID = st.session_state.session_id

# --------------------------------
# CACHED DIALOGFLOW CLIENT
# --------------------------------
@st.cache_resource
def get_dialogflow_client():
    return dialogflow.SessionsClient(
        client_options=ClientOptions(
            api_endpoint="dialogflow.googleapis.com"
        )
    )

session_client = get_dialogflow_client()

# --------------------------------
# DIALOGFLOW FUNCTION
# --------------------------------
def detect_intent(text: str) -> str:
    session = session_client.session_path(PROJECT_ID, SESSION_ID)

    text_input = dialogflow.TextInput(
        text=text,
        language_code=LANGUAGE_CODE
    )

    query_input = dialogflow.QueryInput(text=text_input)

    response = session_client.detect_intent(
        request={
            "session": session,
            "query_input": query_input
        }
    )

    return response.query_result.fulfillment_text

# --------------------------------
# STREAMLIT UI
# --------------------------------
st.set_page_config(page_title="GLIM Carpool", page_icon="🚗")
st.title("🚗 GLIM Carpool Assistant")
st.caption("Find rides, check status, and confirm groups")

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# User input
user_input = st.chat_input("Type your message here...")

if user_input:
    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )
    with st.chat_message("user"):
        st.write(user_input)

    with st.spinner("Contacting GLIM Carpool..."):
        try:
            reply = detect_intent(user_input)
        except Exception as e:
            reply = f"❌ Dialogflow error: {e}"

    st.session_state.messages.append(
        {"role": "assistant", "content": reply}
    )
    with st.chat_message("assistant"):
        st.write(reply)

# --------------------------------
# DEBUG (REMOVE LATER)
# --------------------------------
with st.expander("🔍 Debug Info"):
    st.write("Project ID:", PROJECT_ID)
    st.write("Session ID:", SESSION_ID)
    st.write(
        "Credentials file exists:",
        os.path.exists(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ""))
    )
