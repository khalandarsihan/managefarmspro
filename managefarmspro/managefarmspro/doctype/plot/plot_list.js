frappe.listview_settings["Plot"] = {
	hide_name_column: true,
	hide_name_filter: true,
	onload: function (listview) {
		// Hide the 'Add Plot' button
		listview.page.btn_primary.hide();
	},
	formatters: {
		maintenance_balance: function (value) {
			if (value < 1000) {
				return `<span style="color: red">${value}</span>`;
			}
			return value;
		},
	},
};
