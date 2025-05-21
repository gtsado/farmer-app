# main.py

import streamlit as st
from database.db import create_tables
create_tables()

# Import Views
from views.token_management import run_token_management
from views.farmers import run_farmers
from views.cocoa_delivery import run_cocoa_delivery
from views.lender import run_lender_management
from views.tips import run_tips
# from views.dashboard import run_dashboard


def main():
	st.set_page_config(page_title="EcoWise Internal App", layout="wide")
	st.title("EcoWise Internal Platform")

	menu = [
		"Home",
		"Token Management",
		"Farmers",
		"Cocoa Delivery",
		"Lender & Bundle Management",
		"Tips",
		"Dashboard"
	]

	choice = st.sidebar.selectbox("Select Page", menu)

	if choice == "Home":
		st.subheader("Welcome to the EcoWise Internal App")
		st.write("Use the sidebar to navigate between modules.")
	elif choice == "Token Management":
		run_token_management()
	elif choice == "Farmers":
		run_farmers()
	elif choice == "Cocoa Delivery":
		run_cocoa_delivery()
	elif choice == "Lender & Bundle Management":
		run_lender_management()
	# elif choice == "Lender Dashboard":
	# 	run_lender_dashboard()
	# elif choice == "Bundles":
	# 	run_bundles()
	elif choice == "Tips":
		run_tips()
	elif choice == "Dashboard":
		run_dashboard()


if __name__ == '__main__':
	main()
