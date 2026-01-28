import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import requests
from login import login_screen

API_URL = "http://127.0.0.1:8000/ask"

st.set_page_config(page_title="HR Compliance Assistant", page_icon="🤖")


# ---------------------------
# Login Check
# ---------------------------
if "user" not in st.session_state:
    login_screen()
    st.stop()

user = st.session_state["user"]

st.sidebar.success(f"Logged in as: {user['name']} ({user['role']})")

st.title("🤖 HR Compliance Smart Assistant")


# ---------------------------
# Chat History
# ---------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ---------------------------
# Chat Input
# ---------------------------
query = st.chat_input("Ask your HR question...")

if query:

    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):

            response = requests.post(API_URL, json={
                "question": query,
                "user": user
            })

            data = response.json()
            answer = data["answer"]

            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
