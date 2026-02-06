import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import requests
import pandas as pd
from login import login_screen

API_URL = "http://127.0.0.1:8000/ask"
UPLOAD_URL = "http://127.0.0.1:8000/upload"

DATA_FOLDER = "./data"

st.set_page_config(page_title="HR Compliance Assistant", page_icon="🤖")


# ---------------------------
# Login Check
# ---------------------------
if "user" not in st.session_state:
    login_screen()
    st.stop()

user = st.session_state["user"]
role = user["role"]

st.sidebar.success(f"Logged in as: {user['name']} ({role})")

st.title("🤖 HR Compliance Smart Assistant")


# =====================================================
# ✅ ADMIN PANEL: File Manager + Upload
# =====================================================
if role == "admin":

    st.sidebar.markdown("## 📂 Admin File Manager")

    # Ensure folder exists
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

    # List files in /data
    files = os.listdir(DATA_FOLDER)

    if files:

        selected_file = st.sidebar.selectbox(
            "Select a file",
            files
        )

        action = st.sidebar.radio(
            "Choose Action",
            ["👁 View File", "❌ Delete File"]
        )

        file_path = os.path.join(DATA_FOLDER, selected_file)

        # ---------------------------
        # View File
        # ---------------------------
        if action == "👁 View File":

            st.sidebar.info(f"Viewing: {selected_file}")

            try:
                # CSV Preview
                if selected_file.endswith(".csv"):
                    df = pd.read_csv(file_path)
                    st.subheader("📊 CSV Preview")
                    st.dataframe(df)

                # Excel Preview
                elif selected_file.endswith(".xlsx"):
                    df = pd.read_excel(file_path)
                    st.subheader("📊 Excel Preview")
                    st.dataframe(df)

                # Text Preview
                elif selected_file.endswith(".txt"):
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    st.subheader("📄 Text File Content")
                    st.text(content)

                # PDF / DOCX cannot preview directly
                elif selected_file.endswith(".pdf") or selected_file.endswith(".docx"):
                    st.warning("PDF/DOCX preview not supported inside Streamlit.")

                else:
                    st.warning("Unsupported file format")

            except Exception as e:
                st.error(f"❌ Error reading file: {e}")

        # ---------------------------
        # Delete File
        # ---------------------------
        elif action == "❌ Delete File":

            st.sidebar.warning("This action is permanent!")

            if st.sidebar.button("Confirm Delete"):

                os.remove(file_path)

                st.sidebar.success(f"✅ Deleted: {selected_file}")
                st.rerun()

    else:
        st.sidebar.warning("⚠️ No files found in /data folder")


    # =====================================================
    # Upload New File
    # =====================================================
    st.sidebar.markdown("## ➕ Add New File")

    uploaded_file = st.sidebar.file_uploader(
        "Upload Document or Dataset",
        type=["pdf", "docx", "txt", "csv", "xlsx"]
    )

    if uploaded_file:

        st.sidebar.info("Uploading...")

        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}

        response = requests.post(UPLOAD_URL, files=files)

        if response.status_code == 200:
            st.sidebar.success("✅ File Uploaded & Indexed Successfully!")
            st.rerun()

        else:
            st.sidebar.error("❌ Upload Failed")
            st.sidebar.code(response.text)


# =====================================================
# CHAT HISTORY
# =====================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# =====================================================
# CHAT INPUT
# =====================================================
query = st.chat_input("Ask your HR question...")

if query:

    # Store user message
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    # Assistant Response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):

            response = requests.post(API_URL, json={
                "question": query,
                "user": user
            })

            if response.status_code != 200:
                st.error("❌ Backend Error")
                st.code(response.text)
                answer = "❌ Backend failed. Please check FastAPI logs."

            else:
                try:
                    data = response.json()
                    answer = data.get("answer", "⚠️ No answer returned")
                    st.markdown(answer)

                except Exception:
                    st.error("❌ Invalid JSON Response from API")
                    st.code(response.text)
                    answer = "❌ API returned invalid response."

    # Store assistant reply
    st.session_state.messages.append({"role": "assistant", "content": answer})
