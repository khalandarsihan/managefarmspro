# Copyright (c) 2025, FigAi GenAi Solutions and contributors
# For license information, please see license.txt


import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}
    
    # Set default maintenance balance if not provided
    if 'maintenance_balance' not in filters:
        filters['maintenance_balance'] = 500
        
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "fieldname": "plot_name",
            "label": _("Plot Name"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "customer_name",
            "label": _("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": 150
        },
        {
            "fieldname": "cluster",
            "label": _("Cluster"),
            "fieldtype": "Link",
            "options": "Cluster",
            "width": 120
        },
        {
            "fieldname": "plot_status",
            "label": _("Status"),
            "fieldtype": "Select",
            "width": 100
        },
        {
            "fieldname": "monthly_maintenance_budget",
            "label": _("Monthly Budget"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "total_amount_spent",
            "label": _("Amount Spent"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "maintenance_balance",
            "label": _("Balance"),
            "fieldtype": "Currency",
            "width": 120
        }
    ]

def get_data(filters):
    conditions = ["monthly_maintenance_budget > 0"]  # Base condition to filter out zero budgets
    
    # Add maintenance balance condition
    if filters.get('maintenance_balance'):
        conditions.append("maintenance_balance <= %(maintenance_balance)s")
    
    if filters.get("cluster"):
        conditions.append("cluster = %(cluster)s")
    
    if filters.get("plot_status"):
        conditions.append("plot_status = %(plot_status)s")
    
    where_clause = " WHERE " + " AND ".join(conditions)
    
    return frappe.db.sql(f"""
        SELECT
            plot_name,
            customer_name,
            cluster,
            plot_status,
            monthly_maintenance_budget,
            total_amount_spent,
            maintenance_balance
        FROM `tabPlot`
        {where_clause}
        ORDER BY maintenance_balance ASC, plot_name ASC
    """, filters, as_dict=1)