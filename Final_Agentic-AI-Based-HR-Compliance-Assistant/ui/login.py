import streamlit as st
import sys, os
sys.path.append("..")
from auth.auth_service import authenticate



def login_screen():
    st.title("🔐 HR Compliance Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        user = authenticate(username, password)

        if user:
            st.session_state["user"] = user
            st.success(f"Welcome {user['name']} ({user['role']})")
            st.rerun()
        else:
            st.error("Invalid username or password")
