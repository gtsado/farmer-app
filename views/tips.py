import streamlit as st
import pandas as pd
from database.db import get_farmer_list, create_tip, get_all_tips

def run_tips():
    st.title("Tips")

    tab1, tab2 = st.tabs(["➕ Give Tip", "📋 History"])

    # --- Tab 1: Give Tip ---
    with tab1:
        st.subheader("Mint Tip (as Internal Tokens)")
        farmers = get_farmer_list()
        if not farmers:
            st.info("No farmers registered yet.")
        else:
            opts = {label: fid for fid, label in farmers}
            sel = st.selectbox("Select Farmer", list(opts.keys()))
            amount = st.number_input("Tip Amount", min_value=0.0, step=1.0)
            desc = st.text_input("Description", value="Farmer tip")
            if st.button("Give Tip"):
                if amount <= 0:
                    st.error("Please enter a positive amount.")
                else:
                    tip_id = create_tip(opts[sel], amount, desc)
                    st.success(f"Minted {amount} internal tokens as Tip `{tip_id}` to {sel}.")

    # --- Tab 2: History ---
    with tab2:
        st.subheader("Tip History")
        df = get_all_tips()
        if df.empty:
            st.info("No tips have been given yet.")
        else:
            st.dataframe(df, use_container_width=True)
