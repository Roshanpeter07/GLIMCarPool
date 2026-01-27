# ================================
# app.py — GLIM Carpool (Fixed)
# ================================

import os
import json
import uuid
import tempfile
import streamlit as st

# --------------------------------
# 1. SET GOOGLE CREDENTIALS (ONCE)
# --------------------------------
if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
    creds = json.loads(st.secrets["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
    with tempfile.NamedTemporaryFile(delete=False) as f:
        json.dump(creds, f)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name

# --------------------------------
# 2. IMPORT DIALOGFLOW (AFTER CREDS)
# --------------------------------
from google.cloud import dialogflow
from google.api_core.client_options import ClientOptions

# --------------------------------
# 3. CONSTANTS
# --------------------------------
PROJECT_ID = "solopool-mvp-xapu"
LANGUAGE_CODE = "en"

# --------------------------------
# 4. SESSION ID (PERSISTENT)
# --------------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

SESSION_ID = st.session_state.session_id

# --------------------------------
# 5. CACHE DIALOGFLOW CLIENT
# --------------------------------
@st.cache_resource
def get_dialogflow_client():
    options = ClientOptions(api_endpoint="dialogflow.googleapis.com")
    return dialogflow.SessionsClient(client_options=options)

session_client = get_dialogflow_client()

# --------------------------------
# 6. DIALOGFLOW QUERY FUNCTION
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
# 7. STREAMLIT UI
# --------------------------------
st.set_page_config(page_title="GLIM Carpool", page_icon="🚗")
st.title("🚗 GLIM Carpool Assistant")

st.caption("Find a ride, check your status, or confirm a group.")

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
    # Show user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):
        st.write(user_input)

    # Call Dialogflow ONLY ON SUBMIT
    with st.spinner("Contacting GLIM Carpool..."):
        try:
            reply = detect_intent(user_input)
        except Exception as e:
            reply = f"❌ Error connecting to Dialogflow: {str(e)}"

    # Show bot reply
    st.session_state.messages.append({
        "role": "assistant",
        "content": reply
    })

    with st.chat_message("assistant"):
        st.write(reply)

# --------------------------------
# 8. DEBUG (OPTIONAL — REMOVE LATER)
# --------------------------------
with st.expander("🔍 Debug Info"):
    st.write("Project ID:", PROJECT_ID)
    st.write("Session ID:", SESSION_ID)
