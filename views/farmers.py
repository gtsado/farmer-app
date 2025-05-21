# views/farmers.py

import streamlit as st
from database.db import (
    create_farmer,
    get_all_farmers,
    get_farmer_list,
    create_sack_and_mint_token,
    get_sacks_by_farmer
)

def run_farmers():
    st.title("Farmer Management")

    tab1, tab2, tab3, tab4 = st.tabs([
        "➕ Register Farmer",
        "📋 View Farmers",
        "🧺 Deliver Cocoa Sack",
        "📜 Sack History"
    ])

    # Tab 1: Register Farmer
    with tab1:
        st.subheader("Register New Farmer")

        with st.form("farmer_form"):
            first_name = st.text_input("First Name")
            last_name = st.text_input("Last Name")
            email = st.text_input("Email")
            country = st.text_input("Country")
            city = st.text_input("City")
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            phone = st.text_input("Phone Number")

            submitted = st.form_submit_button("Register Farmer")
            if submitted:
                if not first_name or not last_name:
                    st.error("First and Last Name are required.")
                else:
                    create_farmer(first_name, last_name, email, country, city, gender, phone)
                    st.success(f"✅ Registered {first_name} {last_name}")

    # Tab 2: View/Search Farmers
    with tab2:
        st.subheader("Registered Farmers")

        df = get_all_farmers()

        if df.empty:
            st.info("No farmers have been registered yet.")
        else:
            search_term = st.text_input("Search farmers by any field")

            if search_term:
                df_filtered = df[df.apply(lambda row: search_term.lower() in row.astype(str).str.lower().to_string(), axis=1)]
                st.write(f"Found {len(df_filtered)} match(es)")
                st.dataframe(df_filtered, use_container_width=True)
            else:
                st.write(f"Total Farmers: {len(df)}")
                st.dataframe(df, use_container_width=True)

    # Tab 3: Deliver Cocoa Sack
    with tab3:
        st.subheader("Record Sack Delivery")

        farmers = get_farmer_list()
        if not farmers:
            st.warning("No farmers registered yet.")
            return

        farmer_options = {label: fid for fid, label in farmers}
        selected_label = st.selectbox("Select Farmer", list(farmer_options.keys()))
        selected_farmer_id = farmer_options[selected_label]

        with st.form("sack_form"):
            weight_kg = st.number_input("Weight (kg)", min_value=1.0, step=0.5)
            value_paid = st.number_input("Value Paid", min_value=0.0, step=100.0)
            warehouse = st.text_input("Warehouse / Shed")
            use_now = st.checkbox("Use current time as delivery time", value=True)
            delivered_at = None
            if not use_now:
                delivered_at = st.datetime_input("Delivery Date & Time")

            sack_submit = st.form_submit_button("Record Delivery")

            if sack_submit:
                if weight_kg > 0 and value_paid > 0 and warehouse:
                    sack_id = create_sack_and_mint_token(
                        selected_farmer_id, weight_kg, value_paid, warehouse,
                        None if use_now else delivered_at.isoformat()
                    )
                    st.success(f"Sack `{sack_id}` recorded and debt token minted.")
                else:
                    st.error("Please fill in all required fields.")

    # Tab 4: Sack History
    with tab4:
        st.subheader("View Sack Delivery History by Farmer")

        farmers = get_farmer_list()
        if not farmers:
            st.warning("No farmers registered yet.")
        else:
            farmer_options = {label: fid for fid, label in farmers}
            selected_label = st.selectbox("Select Farmer to View Sacks", list(farmer_options.keys()),
                                          key="history_select")
            selected_farmer_id = farmer_options[selected_label]

            df_sacks = get_sacks_by_farmer(selected_farmer_id)

            if df_sacks.empty:
                st.info("This farmer has not delivered any sacks yet.")
            else:
                st.write(f"Total Sacks Delivered: {len(df_sacks)}")
                st.dataframe(df_sacks, use_container_width=True)
