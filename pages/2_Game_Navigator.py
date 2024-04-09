import streamlit as st
from pages_content.game_navigator_content import content_immortal_game_game_navigator, content_lichess_game_navigator


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

# --- page content
if st.session_state.get("platform") == "Immortal Game":
    content_immortal_game_game_navigator()
elif st.session_state.get("platform") == "Lichess":
    content_lichess_game_navigator()

