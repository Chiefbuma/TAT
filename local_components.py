# local_components.py

import streamlit as st

def card_container(title, body, color="lightblue"):
    with st.container():
        st.markdown(
            f"""
            <div style="background-color:{color};padding:1rem;border-radius:10px;margin-bottom:1rem">
                <h3 style="margin:0;">{title}</h3>
                <p>{body}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
