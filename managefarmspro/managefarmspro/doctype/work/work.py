import frappe
from frappe.model.document import Document


class Work(Document):
	pass


# Standalone function to calculate total_cost
def calculate_total_cost(doc, method):
	total_cost = 0

	# Sum up total prices from the equipment_table
	if doc.equipment_table:
		for row in doc.equipment_table:
			total_cost += row.total_price or 0

	# Sum up total prices from the material_table
	if doc.material_table:
		for row in doc.material_table:
			total_cost += row.total_price or 0

	# Sum up total prices from the labor_table
	if doc.labor_table:
		for row in doc.labor_table:
			total_cost += row.total_price or 0

	# Update the total_cost field in the document
	doc.total_cost = total_cost


# Function to update Work Child table in Plot Doctype
def update_work_child(doc, method):
	# Get the corresponding Plot document
	plot_doc = frappe.get_doc("Plot", doc.plot)

	# Mapping for docstatus values
	status_mapping = {0: "Draft", 1: "Submitted", 2: "Cancelled"}

	# Determine the status based on docstatus
	status = status_mapping.get(doc.docstatus, "Unknown")

	# Prepare the data to be added to the Work Child table
	work_data = {
		"work_id": doc.name,
		"work_name": doc.work_type_name,
		"work_date": doc.work_date,
		"status": status,  # Standard status from docstatus
		"total_cost": doc.total_cost,
	}

	# Check if the Work entry already exists in the child table
	existing_work = next((work for work in plot_doc.work_details if work.work_id == doc.name), None)

	if existing_work:
		# Update the existing row
		existing_work.work_date = work_data["work_date"]
		existing_work.work_name = work_data["work_name"]
		existing_work.status = work_data["status"]
		existing_work.total_cost = work_data["total_cost"]
	else:
		# Add a new row to the Work Child table
		plot_doc.append("work_details", work_data)

	# Save the Plot document
	plot_doc.save()
