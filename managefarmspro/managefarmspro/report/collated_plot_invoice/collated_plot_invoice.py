import os
import frappe
import json
from frappe.utils.pdf import get_pdf
from frappe import _

@frappe.whitelist()
def execute(filters=None):
    """Generate report data and return columns, data for Frappe query report."""
    columns = get_columns()
    data, grand_total, supervision_charge = get_data(filters)
    return columns, data

def get_columns():
    """Define and return the column structure for the report."""
    return [
        {"fieldname": "plot", "label": "Plot", "fieldtype": "Link", "options": "Plot", "width": 150},
        {"fieldname": "work_date", "label": "Work Date", "fieldtype": "Date", "width": 120},
        {"fieldname": "work_name", "label": "Work Name", "fieldtype": "Data", "width": 180},
        {"fieldname": "work_id", "label": "Work ID", "fieldtype": "Data", "width": 150},
        {"fieldname": "description", "label": "Description", "fieldtype": "Data", "width": 250},
        {"fieldname": "total_cost", "label": "Total Cost", "fieldtype": "Currency", "width": 120}
    ]

def get_data(filters):
    """Fetch and structure data for the report based on the provided filters."""
    plot_name = filters.get('plot')
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')

    conditions = "WHERE docstatus = 1 AND (invoice_number IS NULL OR invoice_number = '')"
    if plot_name:
        conditions += f" AND plot = '{plot_name}'"
    if start_date and end_date:
        conditions += f" AND work_date BETWEEN '{start_date}' AND '{end_date}'"

    invoices = frappe.db.sql(f"""
        SELECT 
            name AS work_id,
            plot,
            (SELECT plot_name FROM `tabPlot` WHERE `tabPlot`.name = `tabWork`.plot) AS plot_name,  
            work_date,
            work_type_name AS work_name,  
            description,
            total_cost,
            customer
        FROM `tabWork`
        {conditions}
        ORDER BY work_date ASC
    """, as_dict=True)

    grand_total = 0
    supervision_charge = 0
    for invoice in invoices:
        grand_total += invoice.get("total_cost", 0) or 0

        plot_details = frappe.db.get_value('Plot', invoice.get('plot'), ['customer_name', 'plot_name', 'supervision_charge'], as_dict=True)
        invoice['customer'] = invoice.get("customer") or plot_details.get('customer_name', 'N/A')
        invoice['plot_name'] = plot_details.get('plot_name') if plot_details else 'N/A'
        
        supervision_percent = plot_details.get('supervision_charge') if plot_details else 0
        invoice_supervision_charge = (supervision_percent / 100) * invoice.get("total_cost", 0)
        supervision_charge += invoice_supervision_charge

        # Fetch item names from Item Doctype and include them
        labor_details = frappe.get_all(
            "Labor Child",
            filters={'parent': invoice.get("work_id")},
            fields=[
                "labor_name as item_code", 
                "number_of_labor_units as qty", 
                "labor_unit as unit", 
                "unit_price as rate",  # Include rate
                "total_price as amount", 
                "'Labor' as item_group"
            ]
        )
        equipment_details = frappe.get_all(
            "Equipment Child",
            filters={'parent': invoice.get("work_id")},
            fields=[
                "item_name as item_code", 
                "number_of_equipment_units as qty", 
                "equipment_unit as unit", 
                "unit_price as rate",  # Include rate
                "total_price as amount", 
                "'Equipment' as item_group"
            ]
        )
        material_details = frappe.get_all(
            "Material Child",
            filters={'parent': invoice.get("work_id")},
            fields=[
                "material_name as item_code", 
                "number_of_material_units as qty", 
                "material_unit as unit", 
                "unit_price as rate",  # Include rate
                "total_price as amount", 
                "'Raw Material' as item_group"
            ]
        )

        # Map item codes to item names
        for item in labor_details + equipment_details + material_details:
            item['item_name'] = frappe.db.get_value("Item", item['item_code'], "item_name") or item['item_code']

        # Combine the details into one list of items
        invoice['items'] = labor_details + equipment_details + material_details

        # Ensure items are initialized
        invoice['items'] = invoice['items'] if invoice['items'] else []

    return invoices, grand_total, supervision_charge


@frappe.whitelist()
def download_invoice_pdf(filters):
    """
    Generate a consolidated Sales Invoice PDF, link the invoice number to each work entry,
    and create a Sales Invoice entry in Frappe.
    """
    if isinstance(filters, str):
        filters = json.loads(filters)

    invoices, grand_total, supervision_charge = get_data(filters)
    if not invoices:
        frappe.throw(_("No new work entries found for generating the invoice."))

    final_grand_total = grand_total + supervision_charge

    customer = invoices[0].get("customer", None)
    plot_name = invoices[0].get("plot", "N/A")

    if not customer or not frappe.db.exists("Customer", customer):
        frappe.throw(_("Customer not found for this plot. Please ensure a valid customer is assigned."))

    company = "Philosan Farm Management"
    income_account = frappe.db.get_value("Company", company, "default_income_account")
    if not income_account:
        frappe.throw(_("Please set a default income account for the company {0}.").format(company))

    supervision_charge_account = "Service - PFM"

    # Create a new Sales Invoice with stock update enabled
    sales_invoice = frappe.get_doc({
        "doctype": "Sales Invoice",
        "customer": customer,
        "company": company,
        "plot": plot_name,
        "posting_date": filters.get('start_date'),
        "due_date": filters.get('end_date'),
        "update_stock": 1,
        "set_warehouse": "Main Warehouse - PFM",
        "cost_center": "Main - PFM",
        "items": []
    })

    for invoice in invoices:
        item_name = invoice.get('work_name')
        invoice_item = {
            "item_name": item_name,
            "description": invoice.get("description"),
            "qty": 1,
            "rate": invoice.get("total_cost"),
            "amount": invoice.get("total_cost"),
            "linked_work_entry": invoice.get("work_id"),
            "income_account": income_account,
            "warehouse": "Main Warehouse - PFM",
            "expense_account": "Cost of Goods Sold - PFM",
            "plot": plot_name,
            "work_id": invoice.get("work_id")
        }
        sales_invoice.append("items", invoice_item)

    if supervision_charge > 0:
        additional_charge_item = {
            "item_name": "Supervision Charges",
            "description": "Supervision charges for the services provided.",
            "qty": 1,
            "rate": supervision_charge,
            "amount": supervision_charge,
            "income_account": supervision_charge_account
        }
        sales_invoice.append("items", additional_charge_item)

    sales_invoice.total = grand_total
    sales_invoice.total_taxes_and_charges = 0
    sales_invoice.total_amount = final_grand_total
    sales_invoice.grand_total = final_grand_total
    sales_invoice.rounded_total = final_grand_total
    sales_invoice.outstanding_amount = final_grand_total

    sales_invoice.insert()
    sales_invoice.submit()

    invoice_number = sales_invoice.name

    for invoice in invoices:
        frappe.db.set_value("Work", invoice["work_id"], "invoice_number", invoice_number)

    for invoice in invoices:
        invoice['invoice_items'] = invoice.pop('items', []) if invoice.get('items') is not None else []

    context = {
        'invoices': invoices,
        'grand_total': grand_total,
        'supervision_charge': supervision_charge,
        'final_grand_total': final_grand_total,
        'filters': filters,
        'invoice_number': invoice_number,
        'customer': customer,
        'plot_name': plot_name
    }

    html = frappe.render_template("managefarmspro/templates/collated_invoice.html", context)
    pdf_file = get_pdf(html)
    
    # Retrieve the plot ID from the provided filters
    plot_id = filters.get('plot')
    
    # Fetch the plot name from the database using the plot ID.
    # If the plot name is not found, default to "N/A".
    plot_name = frappe.db.get_value('Plot', plot_id, 'plot_name') or "N/A"

    
    # Construct the file name using the plot name
    file_name = f"Invoice_{plot_name}_{filters.get('start_date')}_{filters.get('end_date')}.pdf"

    file_path = f"public/files/{file_name}"
    full_file_path = frappe.get_site_path(file_path)

    os.makedirs(os.path.dirname(full_file_path), exist_ok=True)

    with open(full_file_path, "wb") as f:
        f.write(pdf_file)

    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "file_url": f"/files/{file_name}",
        "attached_to_doctype": "Sales Invoice",
        "attached_to_name": invoice_number,
    })
    file_doc.insert(ignore_permissions=True)

    site_url = frappe.utils.get_site_url(frappe.local.site)
    file_url = f"{site_url}/files/{file_name}"

    return file_url
