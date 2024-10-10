from frappe import _


def get_context(context):
	# Import necessary libraries
	import frappe
	from frappe import local, session
	from frappe.utils import get_url

	# Check if the user is logged in
	if session.user and session.user != "Guest":
		# Define restricted roles that shouldn't access the home page
		restricted_roles = ["Restricted Role", "Farm Manager"]  # Change these to your custom roles
		user_roles = frappe.get_roles(session.user)

		# If user has any of the restricted roles, redirect to the managefarmspro page
		if any(role in user_roles for role in restricted_roles):
			local.response["type"] = "redirect"
			local.response["location"] = get_url("/app/managefarmspro")
			return
