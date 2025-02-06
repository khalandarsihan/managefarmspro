import frappe
from frappe.model.document import Document
from frappe.utils import add_days
from frappe.utils.file_manager import save_file


class Work(Document):
    def on_submit(self):
        self.update_plot_totals()
        
    def on_cancel(self):
        self.update_plot_totals()
        
    def update_plot_totals(self):
        if self.plot:
            # Get total spent from submitted works
            plot_total = frappe.db.sql("""
                SELECT SUM(total_cost) 
                FROM `tabWork` 
                WHERE plot = %s 
                AND docstatus = 1
            """, self.plot)[0][0] or 0
            
            # Get plot document to access monthly budget
            plot_doc = frappe.get_doc('Plot', self.plot)
            
            # Calculate maintenance balance
            maintenance_balance = (plot_doc.monthly_maintenance_budget or 0) - plot_total
            
            # Update both fields
            frappe.db.set_value('Plot', self.plot, {
                'total_amount_spent': plot_total,
                'maintenance_balance': maintenance_balance
            }, update_modified=False)


# Function to calculate total cost based on child tables
def calculate_total_cost(doc, method):
	total_cost = sum(
		(row.total_price or 0)
		for table in [doc.equipment_table, doc.material_table, doc.labor_table]
		if table
		for row in table
	)
	doc.db_set("total_cost", total_cost, update_modified=False)


# Function to update the Work Child table in the Plot Doctype
def update_work_child(doc, method):
	work_child_data = {
		"work_id": doc.name,
		"work_name": doc.work_type_name,
		"work_date": doc.work_date,
		"status": {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(doc.docstatus, "Unknown"),
		"total_cost": doc.total_cost,
		"parent": doc.plot,
		"parentfield": "work_details",
		"parenttype": "Plot",
	}
	if frappe.db.exists("Work Child", {"parent": doc.plot, "work_id": doc.name}):
		frappe.db.set_value("Work Child", {"parent": doc.plot, "work_id": doc.name}, work_child_data)
	else:
		frappe.get_doc({"doctype": "Work Child", **work_child_data}).insert()


# Create a Sales Invoice from the Work Doctype
# def create_sales_invoice(doc, method=None):
#     invoice = frappe.new_doc("Sales Invoice")
#     invoice.customer = doc.customer
#     invoice.company = frappe.defaults.get_global_default("company")
#     invoice.due_date = add_days(invoice.posting_date, 30)

#     invoice.extend(
#         "items",
#         [
#             {
#                 "item_code": labor.labor_name,
#                 "qty": labor.number_of_labor_units,
#                 "rate": labor.unit_price,
#                 "amount": labor.total_price,
#                 "uom": labor.labor_unit
#             }
#             for labor in (doc.labor_table or [])
#         ] + [
#             {
#                 "item_code": equipment.item_name,
#                 "qty": equipment.number_of_equipment_units,
#                 "rate": equipment.unit_price,
#                 "amount": equipment.total_price,
#                 "uom": equipment.equipment_unit
#             }
#             for equipment in (doc.equipment_table or [])
#         ] + [
#             {
#                 "item_code": material.material_name,
#                 "qty": material.number_of_material_units,
#                 "rate": material.unit_price,
#                 "amount": material.total_price,
#                 "uom": material.material_unit
#             }
#             for material in (doc.material_table or [])
#         ]
#     )

#     invoice.plot = doc.plot
#     invoice.work_id = doc.name
#     invoice.insert(ignore_permissions=True)
#     invoice.submit()
#     doc.db_set("linked_invoice", invoice.name, update_modified=False)

# # Enqueue PDF Generation as a Background Job
# @frappe.whitelist()
# def generate_pdf(doc_name):
#     doc = frappe.get_doc("Work", doc_name)
#     if not doc.linked_invoice:
#         frappe.throw("Linked invoice not found. Cannot generate PDF.")

#     invoice = frappe.get_doc("Sales Invoice", doc.linked_invoice)

#     try:
#         # Generate the PDF and save it
#         pdf_data = frappe.get_print("Sales Invoice", invoice.name, print_format="New SI-3", as_pdf=True)
#         pdf_file = save_file(f"{invoice.name}.pdf", pdf_data, "Sales Invoice", invoice.name, is_private=0)

#         # Link the PDF back to the Work document
#         doc.db_set("invoice_pdf_link", pdf_file.file_url)

#         # Trigger a real-time update to notify the client
#         frappe.publish_realtime("pdf_generated", {"pdf_url": pdf_file.file_url, "doc_name": doc.name})
#         frappe.logger().info(f"PDF for Sales Invoice {invoice.name} generated successfully at {pdf_file.file_url}")
#     except Exception as e:
#         frappe.throw(f"Failed to generate PDF: {str(e)}")
#         frappe.log_error(f"Failed to generate PDF: {str(e)}", "PDF Generation Error")


# # Hooked method for submitting the Work document
# def on_submit(doc, method=None):
#     create_sales_invoice(doc)
#     # Enqueue PDF generation in the background
#     frappe.enqueue('managefarmspro.managefarmspro.doctype.work.work.generate_pdf', doc_name=doc.name)
