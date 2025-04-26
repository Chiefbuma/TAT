# local_components.py
import streamlit as st
from contextlib import contextmanager

@contextmanager
def card_container(key=None):
    with st.container():
        st.markdown(
            """
            <div style="background-color:#f9f9f9;
                        padding:1rem;
                        border-radius:10px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        margin-bottom: 1.5rem;">
            """, unsafe_allow_html=True
        )
        yield
        st.markdown("</div>", unsafe_allow_html=True)
