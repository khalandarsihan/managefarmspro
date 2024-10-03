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

			// Call the server-side method to generate and download the PDF
			frappe.call({
				method: "managefarmspro.managefarmspro.report.collated_plot_invoice.collated_plot_invoice.download_invoice_pdf",
				args: { filters: filters },
				callback: function (response) {
					if (response.message) {
						// Use the returned PDF URL to trigger a direct download and add a timestamp to bypass the cache
						const unique_url = response.message + `?ts=${new Date().getTime()}`;
						window.open(unique_url, "_blank");
						frappe.msgprint(__("PDF generated and saved to File Manager."));
					}
				},
			});
		});
	},
};
