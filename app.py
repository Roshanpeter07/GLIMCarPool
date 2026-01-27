import streamlit as st
import uuid
from google.cloud import dialogflow
from google.api_core.client_options import ClientOptions

# --------------------------------
# CONFIG
# --------------------------------
PROJECT_ID = "solopool-mvp-xapu"
LANGUAGE_CODE = "en"

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
    # Show user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    with st.chat_message("user"):
        st.write(user_input)

    # Get bot response
    with st.spinner("Contacting GLIM Carpool..."):
        try:
            reply = detect_intent(user_input)
        except Exception as e:
            reply = f"❌ Dialogflow error: {e}"

    # Show bot response
    st.session_state.messages.append({
        "role": "assistant",
        "content": reply
    })
    with st.chat_message("assistant"):
        st.write(reply)

# --------------------------------
# DEBUG (REMOVE LATER)
# --------------------------------
with st.expander("🔍 Debug Info"):
    st.write("Project ID:", PROJECT_ID)
    st.write("Session ID:", SESSION_ID)
    st.write(
        "Credentials env var set:",
        "GOOGLE_APPLICATION_CREDENTIALS" in st.secrets
        or "GOOGLE_APPLICATION_CREDENTIALS" in __import__("os").environ
    )
