// frappe.query_reports["Low Balance Plots"] = {
// 	filters: [
// 		{
// 			fieldname: "maintenance_balance_threshold",
// 			label: __("Balance Below"),
// 			fieldtype: "Float", // Changed from Currency to Float
// 			default: 500,
// 			precision: 2,
// 			allow_zero: 1,
// 		},
// 	],
// 	formatter: function (value, row, column, data, default_formatter) {
// 		value = default_formatter(value, row, column, data);

// 		if (
// 			column.fieldname == "maintenance_balance" &&
// 			data.maintenance_balance < "maintenance_balance_threshold"
// 		) {
// 			value = "<span style='color:red'>" + value + "</span>";
// 		}

// 		return value;
// 	},
// };

frappe.query_reports["Low Balance Plots"] = {
	filters: [
		{
			fieldname: "maintenance_balance_threshold",
			label: __("Balance Below"),
			fieldtype: "Float",
			default: 500,
			precision: 2,
			allow_zero: 1,
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname == "maintenance_balance") {
			const threshold = frappe.query_report.get_filter_value(
				"maintenance_balance_threshold"
			);
			if (flt(data.maintenance_balance) <= flt(threshold)) {
				value = "<span style='color:red'>" + value + "</span>";
			}
		}

		return value;
	},
};

/* Copyright (c) 2025, FigAi GenAi Solutions and contributors
For license information, please see license.txt */
