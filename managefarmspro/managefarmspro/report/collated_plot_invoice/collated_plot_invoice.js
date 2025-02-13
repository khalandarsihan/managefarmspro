// frappe.query_reports["Collated Plot Invoice"] = {
// 	filters: [
// 		{
// 			fieldname: "plot",
// 			label: __("Plot"),
// 			fieldtype: "Link",
// 			options: "Plot",
// 			reqd: 1,
// 		},
// 		{
// 			fieldname: "start_date",
// 			label: __("Start Date"),
// 			fieldtype: "Date",
// 			reqd: 1,
// 			default: frappe.datetime.month_start(),
// 		},
// 		{
// 			fieldname: "end_date",
// 			label: __("End Date"),
// 			fieldtype: "Date",
// 			reqd: 1,
// 			default: frappe.datetime.month_end(),
// 		},
// 	],
// 	onload: function (report) {
// 		report.page.add_inner_button(__("Generate Invoice"), function () {
// 			const filters = report.get_values();

// 			// Call the server-side method to generate and download the PDF
// 			frappe.call({
// 				method: "managefarmspro.managefarmspro.report.collated_plot_invoice.collated_plot_invoice.download_invoice_pdf",
// 				args: { filters: filters },
// 				callback: function (response) {
// 					if (response.message) {
// 						// Use the URL returned from the server
// 						var file_url = response.message;

// 						// Open the file in a new tab
// 						window.open(file_url, "_blank");

// 						// Display a success message
// 						frappe.msgprint(__("PDF generated and saved to File Manager."));
// 					}
// 				},
// 			});
// 		});
// 	},
// };
frappe.query_reports["Collated Plot Invoice"] = {
	filters: [
		{
			fieldname: "plot",
			label: __("Plot"),
			fieldtype: "Link",
			options: "Plot",
			reqd: 1,
		},
		{
			fieldname: "start_date",
			label: __("Start Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "end_date",
			label: __("End Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_end(),
		},
	],
	onload: function (report) {
		report.page.add_inner_button(__("Generate Invoice"), function () {
			const filters = report.get_values();
			frappe.call({
				method: "managefarmspro.managefarmspro.report.collated_plot_invoice.collated_plot_invoice.download_invoice_pdf",
				args: { filters: filters },
				callback: function (response) {
					if (response.message) {
						window.open(response.message, "_blank");
						frappe.msgprint(__("PDF generated and saved to File Manager."));
					}
				},
			});
		});
	},
};
