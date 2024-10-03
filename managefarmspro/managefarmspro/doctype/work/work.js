// Copyright (c) 2024, FigAi GenAi Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work', {
    onload: function(frm) {
        // Set a flag to track if the PDF generation message has been shown
        frm.pdf_generated_listener = frm.pdf_generated_listener || false;

        // Set up a WebSocket listener for the PDF generation event
        if (!frm.pdf_generated_listener) {
            frappe.realtime.on('pdf_generated', (data) => {
                // Check if the event is for the current document
                if (data.doc_name === frm.doc.name) {
                    // Show the success message only once
                    frappe.show_alert({
                        message: __("PDF generated successfully!"),
                        indicator: 'green'
                    }, 2);

                    // Reload the form to show the updated PDF link
                    frm.reload_doc();
                }
            });
            // Set the flag to true after attaching the listener
            frm.pdf_generated_listener = true;
        }
    },
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
