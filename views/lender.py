# views/lender.py

import streamlit as st
import pandas as pd

from database.db import (
    create_lender,
    get_all_lenders,
    get_unfunded_bundles,
    get_eligible_sacks_for_bundling,
    create_bundle,
    fund_bundle,
    get_all_bundles_with_details,
    update_lender_position
)

def run_lender_management():
    st.title("Lender & Bundle Management")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Register Lender",
        "View Lenders",
        "Create Bundle",
        "Fund Bundle",
        "View Bundles"
    ])

    # --- Tab 1: Register Lender with Position ---
    with tab1:
        st.subheader("Register a New Lender")
        with st.form("lender_form"):
            wallet = st.text_input("Crypto Wallet Address")
            position = st.number_input("Initial Lending Position", min_value=0.0, step=100.0)
            submitted = st.form_submit_button("Register Lender")
            if submitted:
                if not wallet:
                    st.error("Wallet address is required.")
                else:
                    lender_id = create_lender(wallet, position)
                    st.success(f"Registered Lender `{lender_id}` with position ₦{position}")

    # --- Tab 2: View Lenders & Positions ---
    with tab2:
        st.subheader("All Registered Lenders")
        df_lenders = get_all_lenders() # Fetch lenders for display and selection
        if df_lenders.empty:
            st.info("No lenders registered yet.")
        else:
            df_display = df_lenders.rename(columns={"wallet_address": "Wallet Address", "position": "Current Position"})
            st.dataframe(df_display[["id", "Wallet Address", "Current Position"]], use_container_width=True)

            st.markdown("---")
            st.subheader("Update Lender Position")

            lender_ids = df_lenders["id"].tolist()

            if not lender_ids:
                st.warning("No lenders available to update.")
            else:
                with st.form("update_lender_position_form"):
                    selected_lender_id = st.selectbox(
                        "Select Lender ID",
                        lender_ids,
                        key="update_lender_id_select"
                    )

                    # Get the current position of the selected lender
                    current_pos_series = df_lenders[df_lenders["id"] == selected_lender_id]["position"]
                    current_pos = float(current_pos_series.iloc[0]) if not current_pos_series.empty else 0.0

                    new_position = st.number_input(
                        "New Lending Position",
                        min_value=0.0,
                        step=100.0,
                        value=current_pos, # Pre-fill with current position
                        key="new_lender_position_input"
                    )
                    update_button = st.form_submit_button("Update Position")

                    if update_button:
                        try:
                            update_lender_position(selected_lender_id, new_position)
                            st.success(f"Lender '{selected_lender_id}' position updated to ₦{new_position:,.2f}.")
                            st.experimental_rerun() # Rerun to refresh the table
                        except Exception as e:
                            st.error(f"Error updating lender position: {e}")

    # --- Tab 3: Create Bundle (after filtering eligible sacks) ---
    with tab3:
        st.subheader("Create a New Bundle")

        # Initialize session state variables if they don't exist
        if 'df_eligible_sacks' not in st.session_state:
            st.session_state.df_eligible_sacks = pd.DataFrame()
        if 'bundle_filter_type_val' not in st.session_state:
            st.session_state.bundle_filter_type_val = "None"
        if 'bundle_filter_value_val' not in st.session_state:
            st.session_state.bundle_filter_value_val = ""
        if 'bundle_interest_rate_val' not in st.session_state:
            st.session_state.bundle_interest_rate_val = 0.0
        if 'selected_sack_ids_val' not in st.session_state:
            st.session_state.selected_sack_ids_val = []


        # --- Filter and Interest Rate Parameters (OUTSIDE the form) ---
        # Changes to these will trigger an immediate rerun,
        # allowing you to type in the filter value immediately.
        bundle_filter_type = st.selectbox(
            "Filter Type",
            ["None", "country", "city", "gender", "farmer_name"], # <--- This is where "gender" is added as an option
            key="bundle_filter_type",
            index=["None", "country", "city", "gender", "farmer_name"].index(st.session_state.bundle_filter_type_val)
        )
        st.session_state.bundle_filter_type_val = bundle_filter_type # Update session state

        bundle_filter_value = ""
        if bundle_filter_type != "None":
            if bundle_filter_type == "gender": # Special handling for gender dropdown
                gender_options = ["Male", "Female", "Other"]
                # Ensure value matches one of the options
                default_gender_index = gender_options.index(st.session_state.bundle_filter_value_val) if st.session_state.bundle_filter_value_val in gender_options else 0
                bundle_filter_value = st.selectbox(
                    f"Filter Value ({bundle_filter_type})",
                    gender_options,
                    key="bundle_filter_value_gender", # Unique key for gender selectbox
                    index=default_gender_index
                )
            else: # Text input for other filter types
                bundle_filter_value = st.text_input(
                    f"Filter Value ({bundle_filter_type})",
                    key="bundle_filter_value_text", # Unique key for text input
                    value=st.session_state.bundle_filter_value_val # Set default value
                )
            st.session_state.bundle_filter_value_val = bundle_filter_value # Update session state

        bundle_interest_rate = st.number_input(
            "Interest Rate (%)",
            min_value=0.0,
            step=0.1,
            key="bundle_interest_rate",
            value=st.session_state.bundle_interest_rate_val # Set default value
        )
        st.session_state.bundle_interest_rate_val = bundle_interest_rate # Update session state

        # --- Load Sacks Button (INSIDE its own form) ---
        # This form now only contains the button, ensuring it's the only
        # action that triggers the sack loading logic.
        with st.form("load_sacks_form"): # Changed key to avoid conflict if any
            load_eligible_sacks_button = st.form_submit_button("Load Eligible Sacks")

        # Logic to load sacks only when the button is clicked
        if load_eligible_sacks_button:
            if st.session_state.bundle_filter_type_val == "None":
                st.session_state.df_eligible_sacks = get_eligible_sacks_for_bundling()
            else:
                st.session_state.df_eligible_sacks = get_eligible_sacks_for_bundling(
                    st.session_state.bundle_filter_type_val,
                    st.session_state.bundle_filter_value_val
                )
            # Reset selected sacks when new eligible sacks are loaded
            st.session_state.selected_sack_ids_val = []


        # Display sacks and allow selection only if df_eligible_sacks is not empty
        if not st.session_state.df_eligible_sacks.empty:
            st.dataframe(st.session_state.df_eligible_sacks, use_container_width=True)

            selected_sack_ids = st.multiselect(
                "Select Sacks to Bundle",
                st.session_state.df_eligible_sacks["id"].tolist(),
                format_func=lambda x: (
                    f"{x} (Farmer: {st.session_state.df_eligible_sacks[st.session_state.df_eligible_sacks['id']==x]['farmer_name'].iloc[0]}, "
                    f"Weight: {st.session_state.df_eligible_sacks[st.session_state.df_eligible_sacks['id']==x]['weight_kg'].iloc[0]}kg)"
                ),
                key="selected_sacks",
                default=st.session_state.selected_sack_ids_val # Set default value from session state
            )
            st.session_state.selected_sack_ids_val = selected_sack_ids # Update session state

            if st.button("Create Bundle", key="create_bundle_btn"):
                if st.session_state.selected_sack_ids_val: # Use session state value for check
                    try:
                        new_bundle_id = create_bundle(
                            st.session_state.bundle_filter_type_val,
                            st.session_state.bundle_filter_value_val,
                            st.session_state.bundle_interest_rate_val,
                            st.session_state.selected_sack_ids_val
                        )
                        st.success(f"Bundle `{new_bundle_id}` created with {len(st.session_state.selected_sack_ids_val)} sacks.")
                        # After successful creation, clear the state for a fresh start
                        st.session_state.df_eligible_sacks = pd.DataFrame()
                        st.session_state.selected_sack_ids_val = []
                        st.session_state.bundle_filter_type_val = "None"
                        st.session_state.bundle_filter_value_val = ""
                        st.session_state.bundle_interest_rate_val = 0.0
                        st.experimental_rerun() # Rerun to clear widgets and update display
                    except Exception as e:
                        st.error(f"Error creating bundle: {e}")
                else:
                    st.warning("Please select at least one sack to create a bundle.")
        elif load_eligible_sacks_button and st.session_state.df_eligible_sacks.empty:
            st.info("No eligible sacks found for bundling with the selected criteria.")

    # --- Tab 4: Fund Bundle with Position Check ---
    with tab4:
        st.subheader("Fund an Unfunded Bundle")
        df_lenders = get_all_lenders()  # Fetch lenders for display
        if df_lenders.empty:
            st.warning("Register lenders first.")
            # return # No return here, allow the rest of the tab to load for user experience
        else:
            # Create a dictionary for lender options with their current position
            lender_options_dict = {
                f"{row.id} (Available: ₦{row.position:,.2f})": row.id
                for row in df_lenders.itertuples()
            }
            # Handle empty case for selectbox options
            if not lender_options_dict:
                st.warning("No lenders with available positions found.")
                selected_lender_id = None
                lender_current_position = 0.0
            else:
                selected_lender_label = st.selectbox(
                    "Select Lender",
                    list(lender_options_dict.keys()),
                    key="lender_select"
                )
                selected_lender_id = lender_options_dict[selected_lender_label]
                # Get the actual current position for the selected lender
                lender_current_position_series = df_lenders[df_lenders["id"] == selected_lender_id]["position"]
                lender_current_position = float(
                    lender_current_position_series.iloc[0]) if not lender_current_position_series.empty else 0.0

            df_bundles = get_unfunded_bundles()  # This now includes partially funded bundles with value info
            if df_bundles.empty:
                st.info("No unfunded or partially funded bundles.")
                # return # No return here either
            else:
                # Add current funded amount to bundle options for better display
                bundle_opts = {
                    row.id: f"{row.id} | {row.filter_type}={row.filter_value} | {row.interest_rate}% | Value: ₦{row.total_bundle_value:,.2f} | Funded: ₦{row.funded_amount:,.2f} | Status: {row.status.capitalize()}"
                    for row in df_bundles.itertuples()
                }
                bundle_label = st.selectbox(
                    "Select Bundle to Fund",
                    list(bundle_opts.values()),
                    key="bundle_select"
                )
                # Extract bundle_id from the selected label
                bundle_id = bundle_label.split(' |')[0]

                # Get the selected bundle's total value and current funded amount
                selected_bundle = df_bundles[df_bundles["id"] == bundle_id].iloc[0]
                bundle_total_value = selected_bundle["total_bundle_value"]
                bundle_funded_amount = selected_bundle["funded_amount"]
                bundle_remaining_to_fund = bundle_total_value - bundle_funded_amount

                # Dynamically set max_value for amount input based on
                # MINIMUM of lender's available position and bundle's remaining unfunded amount
                # Ensure it's not negative
                max_allowed_funding = max(0.0, min(lender_current_position, bundle_remaining_to_fund))

                st.info(f"Bundle `{bundle_id}` needs ₦{bundle_remaining_to_fund:,.2f} more to be fully funded.")
                st.info(f"Your available lending position: ₦{lender_current_position:,.2f}")

                amount_to_fund = st.number_input(
                    "Amount to Fund",
                    min_value=0.0,
                    max_value=float(max_allowed_funding),  # Limit by the calculated minimum, ensuring it's not negative
                    step=100.0,
                    key="amount_to_fund"
                )

                if st.button("Fund Bundle", key="fund_bundle_btn"):
                    if selected_lender_id and amount_to_fund > 0:
                        try:
                            funding_id = fund_bundle(selected_lender_id, bundle_id, amount_to_fund)
                            st.success(
                                f"Bundle `{bundle_id}` funded with ₦{amount_to_fund:,.2f} by lender `{selected_lender_id}`. Funding ID: `{funding_id}`.")
                            st.experimental_rerun()  # Refresh to update lender position and bundle status
                        except ValueError as ve:
                            st.error(f"Funding Error: {ve}")
                        except Exception as e:
                            st.error(f"An unexpected error occurred: {e}")
                    else:
                        st.warning("Please select a lender and enter a valid amount to fund.")

    with tab5:
        st.subheader("All Bundles and Their Status")

        bundles_df = get_all_bundles_with_details()

        if bundles_df.empty:
            st.info("No bundles created yet.")
        else:
            # Display relevant columns
            st.dataframe(bundles_df[[
                'bundle_id', 'status', 'calculated_status', 'filter_type', 'filter_value',
                'interest_rate', 'total_bundle_value', 'funded_amount', 'created_at'
            ]], use_container_width=True)

            st.markdown("---")
            st.subheader("Bundle Status Summary")
            status_counts = bundles_df['calculated_status'].value_counts()
            st.write(status_counts)

            # Optional: Display some aggregate statistics
            total_value_all_bundles = bundles_df['total_bundle_value'].sum()
            total_funded_all_bundles = bundles_df['funded_amount'].sum()
            st.metric(label="Total Value of All Bundles", value=f"₦{total_value_all_bundles:,.2f}")
            st.metric(label="Total Amount Funded Across All Bundles", value=f"₦{total_funded_all_bundles:,.2f}")