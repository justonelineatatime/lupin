import streamlit as st

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

with st.sidebar:
    if not st.session_state.get("platform"):
        st.warning("Select a Platform")
    else:
        if st.session_state.get("platform") == "Immortal Game":
            st.image(image="images/IGE-logo.png")
        else:
            st.image(image="images/lichess-logo.jpg")

if not st.session_state.get("platform"):
    st.warning("Select a Platform")
else:
    st.info(f"Platform selected: {st.session_state.get('platform')}")

if not st.session_state.get("platform"):
    st.session_state["platform"] = None

st.divider()
col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
with col2:
    st.image(image="images/IGE-logo.png")
    check_immortal = False
    if st.session_state.get("platform") == "Immortal Game":
        check_immortal = True
    button_immortal = st.button("Select Immortal Game")
    if button_immortal:
        st.session_state["platform"] = "Immortal Game"
        st.rerun()

with col4:
    st.image(image="images/lichess-logo.jpg")
    check_lichess = False
    if st.session_state.get("platform") == "Lichess":
        check_lichess = True
    button_lichess = st.button("Select Lichess")
    if button_lichess:
        st.session_state["platform"] = "Lichess"
        st.rerun()
# ---

if not st.session_state.get("platform"):
    st.stop()

st.divider()
