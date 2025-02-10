// // Copyright (c) 2024, FigAi GenAi Solutions and contributors
// // For license information, please see license.txt

// frappe.ui.form.on("Work", {
// 	onload: function (frm) {
// 		// Set a flag to track if the PDF generation message has been shown
// 		frm.pdf_generated_listener = frm.pdf_generated_listener || false;

// 		// Set up a WebSocket listener for the PDF generation event
// 		if (!frm.pdf_generated_listener) {
// 			frappe.realtime.on("pdf_generated", (data) => {
// 				// Check if the event is for the current document
// 				if (data.doc_name === frm.doc.name) {
// 					// Show the success message only once
// 					frappe.show_alert(
// 						{
// 							message: __("PDF generated successfully!"),
// 							indicator: "green",
// 						},
// 						2
// 					);

// 					// Reload the form to show the updated PDF link
// 					frm.reload_doc();
// 				}
// 			});
// 			// Set the flag to true after attaching the listener
// 			frm.pdf_generated_listener = true;
// 		}
// 	},
// 	// before_submit: function(frm) {
// 	//     frappe.show_alert({
// 	//         message: __("Creating Sales Invoice and generating PDF. Please wait..."),
// 	//         indicator: 'blue'
// 	//     }, 5);
// 	// },
// 	// on_submit: function(frm) {
// 	//     frappe.msgprint(__("Sales Invoice submitted successfully! PDF is being generated in the background."), __("Notification"));
// 	// }
// });

// Copyright (c) 2024, FigAi GenAi Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Work", {
	onload: function (frm) {
		// Set a flag to track if the PDF generation message has been shown
		frm.pdf_generated_listener = frm.pdf_generated_listener || false;

		// Set up a WebSocket listener for the PDF generation event
		if (!frm.pdf_generated_listener) {
			frappe.realtime.on("pdf_generated", (data) => {
				// Check if the event is for the current document
				if (data.doc_name === frm.doc.name) {
					// Show the success message only once
					frappe.show_alert(
						{
							message: __("PDF generated successfully!"),
							indicator: "green",
						},
						2
					);

					// Reload the form to show the updated PDF link
					frm.reload_doc();
				}
			});
			// Set the flag to true after attaching the listener
			frm.pdf_generated_listener = true;
		}
	},

	refresh: function (frm) {
		// Any refresh logic if needed
	},

	plot: function (frm) {
		if (frm.doc.plot) {
			frappe.call({
				method: "managefarmspro.managefarmspro.doctype.work.work.get_plot_balances",
				args: {
					plot: frm.doc.plot,
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value(
							"monthly_maintenance_budget",
							r.message.monthly_maintenance_budget
						);
						frm.set_value("maintenance_balance", r.message.maintenance_balance);
						frm.refresh_fields(["monthly_maintenance_budget", "maintenance_balance"]);
					}
				},
			});
		} else {
			// Clear the fields if plot is cleared
			frm.set_value("monthly_maintenance_budget", 0);
			frm.set_value("maintenance_balance", 0);
			frm.refresh_fields(["monthly_maintenance_budget", "maintenance_balance"]);
		}
	},

	// Commented out sections preserved for reference
	// before_submit: function(frm) {
	//     frappe.show_alert({
	//         message: __("Creating Sales Invoice and generating PDF. Please wait..."),
	//         indicator: 'blue'
	//     }, 5);
	// },
	// on_submit: function(frm) {
	//     frappe.msgprint(__("Sales Invoice submitted successfully! PDF is being generated in the background."), __("Notification"));
	// }
});
