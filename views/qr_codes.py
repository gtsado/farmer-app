# views/qr_codes.py

import streamlit as st
import qrcode
import os
from io import BytesIO
from database.db import (
    get_farmer_profile,
    get_sack_ownership,
    get_bags_for_sack,
    get_batches_for_sack,
    get_bundles_for_sack,
    get_sacks_for_bag,
    get_batch_contributors,
)
from database.db import get_all_sack_ids, get_all_bag_ids, get_all_batch_ids, get_all_farmer_ids

CODES_DIR = os.path.join(os.path.dirname(__file__), "..", "qr_codes")
os.makedirs(CODES_DIR, exist_ok=True)

def run_qr_codes():
    st.title("QR Code Generator & Scanner")

    # --- Use st.query_params for reading parameters (stable API) ---
    params = st.query_params # Changed from st.experimental_get_query_params()
    entity = params.get("entity", None)
    eid    = params.get("id", None)

    if entity and eid:
        st.subheader(f"📖 Details for {entity.upper()} {eid}")
        # dispatch to render detail view
        if entity == "farmer":
            prof = get_farmer_profile(eid)
            if prof is None:
                st.error("No such farmer.")
            else:
                st.markdown("---")
                st.markdown("### Farmer Demographics")
                for k,v in prof.items():
                    if k not in ["total_sacks", "total_weight", "total_value"]:
                        st.write(f"- **{k.replace('_',' ').title()}**: {v}")

                st.markdown("### Cocoa Delivery Summary")
                st.write(f"- **Total Sacks Delivered**: {prof.get('total_sacks', 0)}")
                st.write(f"- **Total Weight Delivered (kg)**: {prof.get('total_weight', 0):,.2f}")
                st.write(f"- **Total Value Delivered (₦)**: {prof.get('total_value', 0):,.2f}")
                st.markdown("---")

        elif entity == "sack":
            info = get_sack_ownership(eid)
            if info is None:
                st.error("No such sack.")
            else:
                st.markdown("### Sack Details")
                st.write(f"- **Sack ID**: {info['sack_id']}")
                st.write(f"- **Farmer**: {info['farmer_name']} (ID: {info['farmer_id']})")
                st.write(f"- **Weight (kg)**: {info['weight_kg']:.2f}")
                st.write(f"- **Value (₦)**: {info['value_paid']:.2f}")
                st.write(f"- **Warehouse**: {info['warehouse']}")
                st.write(f"- **Delivered At**: {info['delivered_at']}")
                st.write(f"- **Bagged In**: {info['bag_id'] or 'Not yet bagged'}")
                st.write(f"- **Batched In**: {info['batch_id'] or 'Not yet batched'}")
                st.write(f"- **Bundled In**: {info['bundle_id'] or 'Not yet bundled'}")

                st.markdown("---")
                st.subheader("Bag & Batch Associations")
                bags_for_sack = get_bags_for_sack(eid)
                batches_for_sack = get_batches_for_sack(eid)
                bundles_for_sack = get_bundles_for_sack(eid)

                if not bags_for_sack.empty:
                    st.write("**Associated Bag(s):**")
                    st.dataframe(bags_for_sack)
                else:
                    st.info("This sack is not yet associated with any bag.")

                if not batches_for_sack.empty:
                    st.write("**Associated Batch(es):**")
                    st.dataframe(batches_for_sack)
                else:
                    st.info("This sack is not yet associated with any batch.")

                if not bundles_for_sack.empty:
                    st.write("**Associated Bundle(s):**")
                    st.dataframe(bundles_for_sack)
                else:
                    st.info("This sack is not yet associated with any bundle.")


        elif entity == "bag":
            st.write("**Sack contributions:**")
            df = get_sacks_for_bag(eid)
            st.dataframe(df[[
                "sack_id","farmer_name","allocated_weight_kg",
                "allocated_value","%_weight","%_value"
            ]])
        elif entity == "batch":
            st.write("**Farmers & Warehouses:**")
            st.table(get_batch_contributors(eid))
        else:
            st.error("Unknown entity type.")
        st.markdown("---")

    # 2) Always show generator
    st.subheader("🔖 Generate QR Code")

    ent = st.selectbox("Entity Type", ["farmer","sack","bag","batch"], index=0)
    # get ID lists for dropdowns
    id_lists = {
        "farmer": get_all_farmer_ids(),
        "sack":   get_all_sack_ids(),
        "bag":    get_all_bag_ids(),
        "batch":  get_all_batch_ids()
    }
    chosen = st.selectbox("Or select an ID", id_lists[ent])
    manual = st.text_input("or paste an ID here")

    if st.button("Generate QR"):
        target_id = manual.strip() or chosen
        if not target_id:
            st.error("Please pick or paste a valid ID.")
        else:
            # --- FIX: Use st.secrets for base URL, with local fallback ---
            # You will set APP_BASE_URL in your Streamlit Cloud secrets.toml
            # For local testing, it defaults to localhost
            base = st.secrets.get("APP_BASE_URL", "http://localhost:8501/")
            url  = f"{base}?entity={ent}&id={target_id}"
            # --- END FIX ---

            # generate QR
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            buf = BytesIO()
            img.save(buf, format="PNG")
            filename = f"{ent}_{target_id}.png"
            filepath = os.path.join(CODES_DIR, filename)
            with open(filepath, "wb") as f:
                buf.seek(0)
                f.write(buf.getvalue())
            st.image(buf.getvalue(), caption="Scan this QR Code", use_container_width=False)
            st.code(url) # Display the URL for easy debugging

    st.markdown("---")
    st.subheader("🔍 View Existing QR Code")

    # 1) Choose entity type
    view_ent = st.selectbox(
        "Entity Type",
        list(id_lists.keys()),
        format_func=lambda e: e.title(),
        key="view_qr_entity"
    )

    # 2) Select from known IDs
    view_id_sel = st.selectbox(
        "Or select an ID",
        id_lists[view_ent],
        key="view_qr_id_sel"
    )
    # 3) Or paste an arbitrary one
    view_id_manual = st.text_input(
        "Or paste an ID here",
        key="view_qr_id_manual"
    )

    # 4) Display QR when requested
    if st.button("View QR Code", key="view_qr_btn"):
        # prefer manual over selection
        view_id = view_id_manual.strip() or view_id_sel
        if not view_id:
            st.error("Please select or paste a valid ID.")
        else:
            filename = f"{view_ent}_{view_id}.png"
            filepath = os.path.join(CODES_DIR, filename)
            if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    img_bytes = f.read()
                st.image(img_bytes, caption=f"QR code for {view_ent} {view_id}")
            else:
                st.warning(f"No QR code found for {view_ent} `{view_id}`. Please generate one first.")