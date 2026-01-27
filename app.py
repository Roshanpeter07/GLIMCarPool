import os
import uuid
import json
import base64
import tempfile
import streamlit as st
from google.cloud import dialogflow
from google.api_core.client_options import ClientOptions

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
PROJECT_ID = "solopool-mvp-xapu"
LANGUAGE_CODE = "en"

# -------------------------------------------------
# LOAD GOOGLE CREDENTIALS FROM BASE64 SECRET
# -------------------------------------------------
if "GOOGLE_APPLICATION_CREDENTIALS_B64" not in st.secrets:
    st.error("Missing GOOGLE_APPLICATION_CREDENTIALS_B64 in Streamlit secrets")
    st.stop()

creds_json = base64.b64decode(
    st.secrets["GOOGLE_APPLICATION_CREDENTIALS_B64"]
).decode("utf-8")

tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
tmp.write(creds_json.encode("utf-8"))
tmp.close()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name

# -------------------------------------------------
# SESSION ID (PERSISTENT)
# -------------------------------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

SESSION_ID = st.session_state.session_id

# -------------------------------------------------
# DIALOGFLOW CLIENT (CACHED)
# -------------------------------------------------
@st.cache_resource
def get_dialogflow_client():
    return dialogflow.SessionsClient(
        client_options=ClientOptions(
            api_endpoint="dialogflow.googleapis.com"
        )
    )

session_client = get_dialogflow_client()

# -------------------------------------------------
# DIALOGFLOW QUERY FUNCTION
# -------------------------------------------------
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

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="GLIM Carpool",
    page_icon="🚗",
    layout="wide"
)

# -------------------------------------------------
# LEFT SIDEBAR — INSTRUCTIONS & PROMPTS
# -------------------------------------------------
st.sidebar.title("How to use GLIM Carpool")

st.sidebar.markdown(
    """
### How to chat
Type your message naturally.  
The assistant will guide you step by step.

### Suggested prompts
Try one of these:
- **"I want to find a ride"**
- **"Book a ride to campus tomorrow"**
- **"Check my ride status"**
- **"Yes"** (to confirm a group)
- **"No"** (to reject a group)

### Tips
- Use your **phone number** consistently
- You can respond **Yes / No** when asked
- The bot will ask follow-up questions automatically
"""
)

st.sidebar.markdown("---")
st.sidebar.caption("GLIM Carpool MVP")

# -------------------------------------------------
# MAIN TITLE
# -------------------------------------------------
st.title("GLIM Carpool Assistant")
st.caption("Find rides, check status, and confirm groups")

# -------------------------------------------------
# TOP-RIGHT DEBUG PANEL
# -------------------------------------------------
top_left, top_right = st.columns([4, 1])

with top_right:
    with st.expander("🛠 Debug", expanded=False):
        st.write("Project ID:", PROJECT_ID)
        st.write("Session ID:", SESSION_ID)
        st.write(
            "Credentials loaded:",
            os.path.exists(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ""))
        )

# -------------------------------------------------
# CHAT HISTORY
# -------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# -------------------------------------------------
# USER INPUT
# -------------------------------------------------
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
