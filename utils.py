from collections import Counter
from typing import List

import pandas as pd
import streamlit as st

ENV = "dev"


def format_milliseconds(ms):
    ms = int(ms)
    # Convert milliseconds to seconds
    total_seconds = ms // 1000

    # Calculate minutes and seconds
    minutes = total_seconds // 60
    seconds = total_seconds % 60

    # Format the string as "00m:00s"
    return f"{minutes:02d}min {seconds:02d}s"


def style_specific_cell(df, row, col, color):
    color = f"background-color: {color}"
    df1 = pd.DataFrame("", index=df.index, columns=df.columns)
    if row >= 0:
        df1.iloc[row, col] = color
    return df1


def most_common(series):
    if len(series) == 0:
        return None
    return Counter(series).most_common(1)[0][0]


def search_user_info_trigger(username):
    st.session_state["username_search"] = username
    st.session_state["user_retreived"] = True


def search_competition_info_trigger(competition_name):
    st.session_state["competition_name_search"] = competition_name
    st.session_state["competition_retrieved"] = True


def clear_cache(exception_list: List[str] = None):
    if not exception_list:
        exception_list = []
    keys = list(st.session_state.keys())
    for key in keys:
        if key not in exception_list:
            st.session_state.pop(key)
