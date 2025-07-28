# views/cocoa_delivery.py

import streamlit as st
import pandas as pd
import json
from database.db import (
    get_farmer_list,
    create_sack_and_mint_token,
    get_unbagged_sacks,
    create_bag_with_sacks,
    auto_fill_bags,
    get_all_bags,
    get_sacks_for_bag,
    create_warrant_receipt,
    get_all_warrant_receipts,
    get_warrant_receipts_by_type,
    get_unbatched_bags,
    create_batch_with_bags,
    auto_fill_batches,
    get_all_batches,
    get_sacks_for_batch,
    get_covered_ids_by_type,
    create_invoice,
    get_all_invoices,
    get_sack_ownership,
    get_bags_for_sack,
    get_batches_for_sack,
    get_bundles_for_sack,
    get_all_sack_ids
)

def run_cocoa_delivery():
    st.title("Cocoa Delivery")

    tab1, tab2, tab3, tab4 ,tab5, tab6, tab7 = st.tabs([
        "📥 Record Sack Delivery",
        "📦 Aggregate Sacks into Bags",
        "🧾 View Bags + Contributions",
        "🔄 Aggregate Bags into Batches",
        "🛡️ CMA Warrant Receipts",
        "Invoices",
        "Track Sack"
    ])

    # === Tab 1: Record Sack Delivery ===
    with tab1:
        st.subheader("Record Cocoa Sack Delivery")

        farmers = get_farmer_list()
        if not farmers:
            st.warning("No farmers registered yet.")
        else:
            farmer_options = {label: fid for fid, label in farmers}
            selected_label = st.selectbox("Select Farmer", list(farmer_options.keys()), key="sack_select")
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
                            selected_farmer_id,
                            weight_kg,
                            value_paid,
                            warehouse,
                            None if use_now else delivered_at.isoformat()
                        )
                        st.success(f"Sack `{sack_id}` recorded and debt token minted.")
                    else:
                        st.error("Please fill in all required fields.")

    # === Tab 2: Aggregate into Bags ===
    with tab2:
        st.subheader("Aggregate Sacks into ≤63kg Bags")

        df = get_unbagged_sacks()

        if df.empty:
            st.info("No unbagged sacks available.")

        df["cumulative_weight"] = df["weight_kg"].cumsum()

        st.write("Unbagged Sacks (cumulative weights help manage 63kg limit):")
        st.dataframe(df[["id", "farmer_name", "weight_kg", "value_paid", "warehouse", "delivered_at", "cumulative_weight"]], use_container_width=True)

        if st.button("Auto-Fill and Aggregate All Eligible Sacks"):
            bag_ids = auto_fill_bags()
            if bag_ids:
                st.success(f"✅ Created {len(bag_ids)} bag(s):")
                for bid in bag_ids:
                    st.write(bid)
                st.rerun()
            else:
                st.info("No eligible sacks found for auto-fill.")



        selected_ids = st.multiselect("Select sacks to include in a bag", options=list(df["id"]))

        if selected_ids:
            total_weight = df[df["id"].isin(selected_ids)]["weight_kg"].sum()
            st.info(f"Total selected weight: {total_weight:.2f} kg")

            if total_weight > 63:
                st.warning("⚠️ Total exceeds 63kg. Please reduce selected sacks.")

            if st.button("Create Bag") and total_weight <= 63:
                # Allocate full weight of each selected sack
                manual_allocations = []
                for sack_id in selected_ids:
                    sack_weight = df[df["id"] == sack_id]["weight_kg"].values[0]
                    manual_allocations.append((sack_id, sack_weight))

                bag_id = create_bag_with_sacks(manual_allocations)
                st.success(f"Bag `{bag_id}` created with {len(manual_allocations)} sack(s).")
                st.rerun()

    with tab3:
        st.subheader("View All Bags + Sack Contributions")

        # 1. pull all bags into a DataFrame
        bags = get_all_bags()
        bag_df = pd.DataFrame(bags, columns=["id", "created_at"])

        if bag_df.empty:
            st.info("No bags have been created yet.")
        else:
            # 2. build a human‐readable label column
            bag_df["label"] = bag_df.apply(
                lambda r: f"{r.id} (created: {r.created_at})", axis=1
            )

            # 3. let user pick by row‐index
            selected_idx = st.selectbox(
                "Select Bag",
                bag_df.index.tolist(),
                format_func=lambda i: bag_df.at[i, "label"],
                key="cocoa_bag_selection6"
            )
            selected_bag_id = bag_df.at[selected_idx, "id"]

            # 4. load and show its sack contributions
            try:
                df_bag = get_sacks_for_bag(selected_bag_id)
                if df_bag.empty:
                    st.warning("No sacks found in this bag.")
                else:
                    total_weight = df_bag["allocated_weight_kg"].sum()
                    total_value = df_bag["allocated_value"].sum()

                    st.write(f"Total Bag Weight: {total_weight:.2f} kg | Estimated Value: ₦{total_value:,.2f}")
                    st.dataframe(df_bag[[
                        "sack_id", "farmer_name", "allocated_weight_kg",
                        "allocated_value", "%_weight", "%_value"
                    ]], use_container_width=True)

                    csv = df_bag.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Download as CSV",
                        csv,
                        f"{selected_bag_id}_sack_contributions.csv",
                        "text/csv"
                    )
            except Exception as e:
                st.error(f"Error loading bag `{selected_bag_id}`:")
                st.text(str(e))

    with tab4:
        st.subheader("Aggregate Bags into 60 MT Batches")

        # Show existing batches
        df_batches = get_all_batches()  # id, weight_mt, product_type, created_at
        if df_batches.empty:
            st.info("No batches created yet.")
        else:
            # compute batch value by summing allocated_value of all sacks in each batch
            df_batches["batch_value"] = df_batches["id"].apply(
                lambda bid: get_sacks_for_batch(bid)["allocated_value"].sum()
            )
            # format for display
            df_batches["weight_mt"] = df_batches["weight_mt"].round(2)
            df_batches["batch_value"] = df_batches["batch_value"].apply(lambda v: f"₦{v:,.2f}")

            st.markdown("**Existing Batches**")
            st.dataframe(
                df_batches[["id", "product_type", "weight_mt", "batch_value", "created_at"]],
                use_container_width=True
            )
        st.markdown("---")
        st.markdown("**Unallocated Bags**")
        # Your manual & auto—batching controls below:
        df = get_unbatched_bags()
        if df.empty:
            st.info("No unbatched bags available.")
        else:
            df["weight_mt"] = (df["weight_kg"]/1000).round(2)
            st.dataframe(df[["id","weight_mt","created_at"]], use_container_width=True)

            # Manual
            chosen = st.multiselect(
                "Select bags for a batch", df["id"].tolist(),
                key="batch_manual_select2"
            )
            if chosen:
                tot_kg = df[df["id"].isin(chosen)]["weight_kg"].sum()
                st.write(f"Total: {tot_kg/1000:.2f} MT")
                if tot_kg > 60000:
                    st.error("Exceeds 60 MT.")
                elif st.button("Create Batch", key="batch_manual_btn3"):
                    batch_id = create_batch_with_bags(chosen, product_type="liquor")
                    st.success(f"Created batch `{batch_id}`")
                    st.rerun()

            st.markdown("---")

            # Auto‐fill
            if st.button("Auto-Fill into Batches", key="batch_auto_btn2"):
                new_bs = auto_fill_batches()
                if new_bs:
                    st.success(f"Created {len(new_bs)} batch(es):")
                    for b in new_bs:
                        st.write(f"• {b}")
                    st.rerun()
                else:
                    st.info("No eligible bags to batch.")

    # --- Tab 5: CMA Warrant Receipts (bags or batches) ---
    with tab5:
        st.subheader("Issue / View CMA Warrant Receipts")

        wr_type = st.selectbox(
            "Receipt type",
            ["pre-processing","post-processing"],
            key="wr_type_select"
        )

        # decide items: bags for pre, batches for post
        if wr_type == "pre-processing":
            items = [r[0] for r in get_all_bags()]
            label = "Select bags to cover"
        else:
            items = get_all_batches()["id"].tolist()
            label = "Select batches to cover"

        covered = get_covered_ids_by_type(wr_type)
        eligible = [i for i in items if i not in covered]

        if not eligible:
            st.info(f"No eligible items for {wr_type}.")
        else:
            sel = st.multiselect(label, eligible, key="wr_sel")
            if st.button("Issue Receipt", key="wr_issue_btn"):
                if not sel:
                    st.error("Pick at least one.")
                else:
                    rid = create_warrant_receipt(wr_type, sel)
                    st.success(f"Issued `{rid}` covering {len(sel)} item(s).")
                    # ADD st.rerun() AFTER THE ACTION
                    st.rerun()

        st.markdown("---")
        dfwr = get_all_warrant_receipts()
        dfwr["covered_ids"] = dfwr["covered_ids"].apply(lambda j: ", ".join(json.loads(j)))
        st.dataframe(dfwr, use_container_width=True)

    with tab6:
        st.subheader("Invoices")

        subtab1, subtab2 = st.tabs(["➕ Create Invoice", "📋 View Invoices"])

        with subtab1:
            df_batches = get_all_batches()
            if df_batches.empty:
                st.info("No batches available.")
            else:
                selected_batches = st.multiselect(
                    "Select Batches for Invoice",
                    df_batches["id"].tolist(),
                    key="invoice_batches"
                )

                # --- ADDED CODE STARTS HERE ---
                total_selected_value = 0.0
                if selected_batches:
                    # Filter df_batches to only include selected ones and sum their total_value
                    filtered_batches_df = df_batches[df_batches['id'].isin(selected_batches)]
                    # --- ADDED CODE: SAFELY ACCESS 'total_value' ---
                    if 'total_value' in filtered_batches_df.columns:
                        total_selected_value = filtered_batches_df['total_value'].sum()
                    else:
                        st.warning(
                            "Warning: 'total_value' column not found for selected batches. Running sum might be inaccurate.")
                        # This warning indicates an underlying data preparation issue.
                        # You might want to inspect your batch creation or sack value allocation if this warning appears frequently.
                # --- END ADDED CODE ---

                st.markdown(f"**Total Value of Selected Batches:** ₦{total_selected_value:,.2f}")
                # --- ADDED CODE ENDS HERE ---

                amt_paid = st.number_input(
                    "Total Amount Paid", min_value=0.0, step=100.0, key="invoice_amt"
                )
                pct_to_farmers = st.number_input(
                    "Percent of Remainder to Farmers",
                    min_value=0, max_value=100, step=1,
                    key="invoice_pct"
                )

                if st.button("Create Invoice", key="invoice_create_btn"):
                    if not selected_batches:
                        st.error("Pick at least one batch.")
                    elif amt_paid <= 0:
                        st.error("Amount must be positive.")
                    else:
                        inv_id = create_invoice(selected_batches, amt_paid, pct_to_farmers)
                        st.success(f"Invoice `{inv_id}` created for {len(selected_batches)} batch(es).")

        with subtab2:
            df_inv = get_all_invoices()
            if df_inv.empty:
                st.info("No invoices issued yet.")
            else:
                df_inv["covered_batches"] = df_inv["covered_batches"].apply(lambda j: ", ".join(json.loads(j)))
                df_inv["percent_to_farmers"] = (df_inv["percent_to_farmers"] * 100).round(2).astype(str) + "%"
                st.dataframe(df_inv, use_container_width=True)
    with tab7:
        st.subheader("Track a Sack Through the Process")

        sack_ids = get_all_sack_ids()
        chosen = st.selectbox("Select Sack ID", sack_ids, key="track_sack_select")
        manual = st.text_input("or paste Sack ID here", key="track_sack_input")

        if st.button("Search", key="track_sack_btn"):
            raw_manual = manual.strip()
            if raw_manual:
                sack_id = raw_manual
            else:
                sack_id = chosen
            if not sack_id:
                st.error("Please select or paste a Sack ID.")
            else:
                # 1) Sack & Farmer info
                info = get_sack_ownership(sack_id)
                if info is None:
                    st.error(f"No sack found with ID `{sack_id}`.")
                else:
                    # ADDED LINES START HERE
                    st.markdown(f"**Sack ID:** {sack_id}")
                    st.markdown(f"**Sack Weight:** {info['weight_kg']} kg")
                    st.markdown(f"**Sack Value:** ₦{info['value_paid']:,}")
                    # ADDED LINES STOP HERE
                    st.markdown(f"**Delivered at:** {info['delivered_at']}")
                    st.markdown(f"**Delivered by:** {info['farmer_name']} (ID: {info['farmer_id']})")

                # 2) Bags
                df_bags = get_bags_for_sack(sack_id)
                if df_bags.empty:
                    st.info("This sack has not been bagged yet.")
                else:
                    st.markdown("**Bags Containing This Sack**")
                    st.dataframe(df_bags, use_container_width=True)

                # 3) Batches
                df_batches = get_batches_for_sack(sack_id)
                if df_batches.empty:
                    st.info("This sack’s bag(s) have not been processed into any batch.")
                else:
                    st.markdown("**Batches Containing This Sack**")
                    df_batches["weight_mt"] = df_batches["weight_mt"].round(2)
                    st.dataframe(df_batches, use_container_width=True)

                # 4) Bundles
                df_bundles = get_bundles_for_sack(sack_id)
                if df_bundles.empty:
                    st.info("This sack has not been included in any financing bundle.")
                else:
                    st.markdown("**Bundles Containing This Sack**")
                    st.dataframe(df_bundles, use_container_width=True)
