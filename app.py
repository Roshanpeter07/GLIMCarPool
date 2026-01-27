import streamlit as st
from google.cloud import dialogflow
import uuid
import os

# --- Configuration ---
if os.path.exists("credentials.json"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath("credentials.json")

PROJECT_ID = "solopool-mvp-xapu" # User must replace this
SESSION_ID = str(uuid.uuid4()) # Unique session per reload
LANGUAGE_CODE = "en"

# --- Page Setup ---
st.set_page_config(page_title="GLIM Carpool", page_icon="🚗")
st.title("🚗 GLIM Carpool")
st.markdown("### Carpooling Matching System")

# --- CSS Styling ---
st.markdown(
    """
    <style>
    .stTextInput > div > div > input {
        border-radius: 10px;
    }
    .chat-message {
        padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; display: flex
    }
    .chat-message.user {
        background-color: #2b313e; color: #ffffff;
    }
    .chat-message.bot {
        background-color: #475063; color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "Welcome to GLIM Carpool! 🚗\n\nI can help you find a carpool group or check your status.\n\nType **'Find a ride'** to start or **'Check status'** to see your details."})
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# --- Dialogflow Function ---
def detect_intent_texts(project_id, session_id, texts, language_code):
    """Returns the result of detect intent with texts as inputs."""
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    text_input = dialogflow.TextInput(text=texts, language_code=language_code)
    query_input = dialogflow.QueryInput(text=text_input)

    try:
        response = session_client.detect_intent(
            request={"session": session, "query_input": query_input}
        )
        fulfillment_text = response.query_result.fulfillment_text
        if not fulfillment_text:
            return "⚠️ No response from Dialogflow. This usually means the **Webhook** is not enabled for this specific intent in the Dialogflow Console. Please check your intent settings."
        return fulfillment_text
    except Exception as e:
        return f"Error connecting to Dialogflow: {e}\n(Make sure credentials are set and Project ID is correct in app.py)"

# --- UI Layout ---
# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get Bot Response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = detect_intent_texts(PROJECT_ID, st.session_state.session_id, prompt, LANGUAGE_CODE)
        message_placeholder.markdown(full_response)
    
    # Add bot message to history
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# --- Sidebar ---
st.sidebar.header("📋 Instructions")
st.sidebar.markdown(
    """
    **How to use:**
    1. Type **"Find a ride"** to start looking for a group.
    2. Provide your Name, Location, Date, and Time.
    3. Type **"Yes"** to confirm if a group is found.
    
    **Check Status:**
    - Type **"Check status"** or **"Who am I with?"** to see your current group and status.
    
    **Reset:**
    - Refresh the page to start a new session.
    """
)
st.sidebar.info("Data is stored in Google Sheets for the admin.")
