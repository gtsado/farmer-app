import streamlit as st
import pandas as pd
from database.db import (
    get_farmer_list,
    get_all_tokens,
    get_token_balance_by_farmer,
    mint_internal_tokens,
    burn_debt_tokens,
    burn_internal_tokens
)

def run_token_management():
    st.title("Token Management")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "View Balances",
        "Mint Internal",
        "Burn Debt",
        "Burn Internal",
        "History"
    ])

    # Tab 1: View Balances
    with tab1:
        st.subheader("Farmer Token Balances")
        farmers = get_farmer_list()
        if not farmers:
            st.info("No farmers registered yet.")
        else:
            opts = {label: fid for fid,label in farmers}
            sel = st.selectbox("Select Farmer", list(opts.keys()))
            df_bal = get_token_balance_by_farmer(opts[sel])
            if df_bal.empty:
                st.info("No tokens for this farmer.")
            else:
                st.dataframe(df_bal, use_container_width=True)

    # Tab 2: Mint Internal Tokens
    with tab2:
        st.subheader("Mint Internal Tokens")
        farmers = get_farmer_list()
        opts = {label: fid for fid,label in farmers}
        sel = st.selectbox("Select Farmer", list(opts.keys()), key="mint_sel")
        amount = st.number_input("Amount to Mint", min_value=0.0, step=1.0)
        desc = st.text_input("Description", value="Manual internal mint")
        if st.button("Mint", key="mint_btn"):
            if amount <= 0:
                st.error("Amount must be positive.")
            else:
                mint_internal_tokens(opts[sel], amount, desc)
                st.success(f"Minted {amount} internal tokens to {sel}.")

    # Tab 3: Burn Debt Tokens
    with tab3:
        st.subheader("Burn Debt Tokens")
        farmers = get_farmer_list()
        opts = {label: fid for fid,label in farmers}
        sel = st.selectbox("Select Farmer", list(opts.keys()), key="burn_sel")
        amount = st.number_input("Amount to Burn", min_value=0.0, step=1.0)
        desc = st.text_input("Description", value="Manual debt burn")
        if st.button("Burn", key="burn_btn"):
            if amount <= 0:
                st.error("Amount must be positive.")
            else:
                burn_debt_tokens(opts[sel], amount, desc)
                st.success(f"Burned {amount} debt tokens from {sel}.")

    with tab4:
        st.subheader("Burn Internal Tokens")
        farmers = get_farmer_list()
        opts = {label: fid for fid, label in farmers}
        sel = st.selectbox("Select Farmer", list(opts.keys()), key="burn_int_sel")
        amount = st.number_input("Amount to Burn", min_value=0.0, step=1.0, key="burn_int_amount")
        desc = st.text_input("Description", value="Manual internal burn", key="burn_int_desc")
        if st.button("Burn Internal", key="burn_int_btn"):
            if amount <= 0:
                st.error("Amount must be positive.")
            else:
                burn_internal_tokens(opts[sel], amount, desc)
                st.success(f"Burned {amount} internal tokens from {sel}.")

    # Tab 5: History (unchanged)
    with tab5:
        st.subheader("All Token Transactions")
        df = get_all_tokens()
        if df.empty:
            st.info("No token transactions yet.")
        else:
            st.dataframe(df, use_container_width=True)