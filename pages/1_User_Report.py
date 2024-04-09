import random

import streamlit as st

from pages_content.user_report_content import content_immortal_game_user_report, content_lichess_user_report

# page setup
st.set_page_config(layout="wide", initial_sidebar_state="collapsed",)
with st.sidebar:
    if not st.session_state.get("platform"):
        st.warning("Select a Platform")
    else:
        if st.session_state.get("platform") == "Immortal Game":
            st.image(image="images/IGE-logo.png")
        else:
            st.image(image="images/lichess-logo.jpg")

if not st.session_state.get("platform"):
    st.switch_page("Platform_Selection.py")

if "editor_key" not in st.session_state:
    st.session_state["editor_key"] = random.randint(0, 100000)

st.session_state["current_move_index"] = 0


# --- page content
if st.session_state.get("platform") == "Immortal Game":
    content_immortal_game_user_report()
elif st.session_state.get("platform") == "Lichess":
    content_lichess_user_report()
