// Copyright (c) 2025, FigAi GenAi Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Low Balance Plots"] = {
	filters: [
		{
			fieldname: "maintenance_balance_threshold",
			label: __("Balance"),
			fieldtype: "Currency",
			default: 500,
			reqd: 1,
		},
	],
};
