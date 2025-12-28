// Enhanced Work Form with ML Predictions
// ManageFarmsPro - Predictive Analytics Integration
// Author: Khalandar Sihan (2303RES181)

frappe.ui.form.on("Work", {
	onload: function (frm) {
		// Set PDF generation listener flag
		frm.pdf_generated_listener = frm.pdf_generated_listener || false;

		// Set up WebSocket listener for PDF generation event
		if (!frm.pdf_generated_listener) {
			frappe.realtime.on("pdf_generated", (data) => {
				// Check if the event is for the current document
				if (data.doc_name === frm.doc.name) {
					frappe.show_alert(
						{
							message: __("PDF generated successfully!"),
							indicator: "green",
						},
						2
					);
					frm.reload_doc();
				}
			});
			frm.pdf_generated_listener = true;
		}

		hideAllSections(frm);

		// Set today's date for 'work_date' if creating a new record and work_date is not set
		if (frm.is_new() && !frm.doc.work_date) {
			frm.set_value("work_date", frappe.datetime.get_today());
		}
	},

	onload_post_render: function (frm) {
		if (!frm.is_new() && frm.doc.invoice_number && !frm.__is_refreshed) {
			frm.__is_refreshed = true;
			frm.reload_doc();
		}
	},

	refresh: function (frm) {
		// ============ ML ANALYTICS BUTTONS ============
		if (frm.doc.docstatus === 0) {
			// Add ML Prediction button for draft works
			frm.add_custom_button(__("🔮 Get ML Prediction"), function () {
				getMLPrediction(frm);
			}, __("ML Analytics")).addClass("btn-info");
			
			// Add Anomaly Check button for existing works with cost
			if (!frm.is_new() && frm.doc.total_cost > 0) {
				frm.add_custom_button(__("🔍 Check Anomaly"), function () {
					checkAnomaly(frm);
				}, __("ML Analytics"));
			}
		}

		// Check if the status is 'Submitted' or 'Cancelled'
		if (frm.doc.docstatus === 1) {
			// Submitted
			frm.clear_custom_buttons();
			frm.toggle_display("labor_table", true);
			frm.toggle_display("equipment_table", true);
			frm.toggle_display("material_table", true);
			
			// Add anomaly check for submitted works
			frm.add_custom_button(__("🔍 Check Anomaly"), function () {
				checkAnomaly(frm);
			});
		} else if (frm.doc.docstatus === 2) {
			// Cancelled
			frm.clear_custom_buttons();
		} else {
			// Add buttons for Draft or amended form
			frm.add_custom_button(__("Add Labor"), function () {
				showLaborFields(frm);
				frm.scroll_to_field("labor_table");
				frm.fields_dict["labor_required"].set_focus();
			}).css({ "background-color": "#4CAF50", color: "white" });

			frm.add_custom_button(__("Add Equipment"), function () {
				showEquipmentFields(frm);
				frm.scroll_to_field("equipment_table");
				frm.fields_dict["equipment_required"].set_focus();
			}).css({ "background-color": "#2196F3", color: "white" });

			frm.add_custom_button(__("Add Material"), function () {
				showMaterialFields(frm);
				frm.scroll_to_field("material_table");
				frm.fields_dict["material_required"].set_focus();
			}).css({ "background-color": "#FFC107", color: "black" });

			checkAndShowChildTables(frm);
		}

		// Description field handling
		if (!frm.is_new() && frm.doc.docstatus === 0) {
			frm.set_df_property("description", "read_only", 0);
		}
		if (frm.doc.docstatus === 1) {
			frm.set_df_property("description", "read_only", 1);
		}

		calculateTotalCost(frm);
		
		// Show prediction hint if plot and work type are set
		if (frm.is_new() && frm.doc.plot && frm.doc.work_type_name) {
			showPredictionHint(frm);
		}
	},

	plot: function (frm) {
		if (frm.doc.plot) {
			frm.fields_dict["work_type_name"].set_focus();

			// Fetch customer details
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Plot",
					fieldname: "customer_name",
					filters: { name: frm.doc.plot },
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value("customer", r.message.customer_name);
					}
				},
			});
			
			// Auto-trigger prediction hint if work type is also set
			if (frm.doc.work_type_name && frm.is_new()) {
				setTimeout(() => showPredictionHint(frm), 500);
			}
		} else {
			// Clear fields if plot is cleared
			frm.set_value("monthly_maintenance_budget", 0);
			frm.set_value("maintenance_balance", 0);
			frm.refresh_fields(["monthly_maintenance_budget", "maintenance_balance"]);
		}
	},

	work_type_name: function (frm) {
		if (frm.doc.work_type_name) {
			frappe.db.get_value("Work Item", frm.doc.work_type_name, "description", function (r) {
				if (r && r.description) {
					frm.set_value("description", r.description);
				}
			});
			
			// Auto-trigger prediction hint if plot is also set
			if (frm.doc.plot && frm.is_new()) {
				setTimeout(() => showPredictionHint(frm), 500);
			}
		}
	},

	description: function (frm) {
		if (frm.doc.description && frm.doc.docstatus === 0) {
			frm.dirty();
		}
	},

	equipment_required: function (frm) {
		autoPopulateUnit(frm, "equipment_required", "equipment_unit");
		frm.fields_dict["equipment_count"].set_focus();
	},

	material_required: function (frm) {
		autoPopulateUnit(frm, "material_required", "material_unit");
		frm.fields_dict["number_of_material_units"].set_focus();
	},

	labor_required: function (frm) {
		autoPopulateUnit(frm, "labor_required", "labor_unit");
		frm.fields_dict["labor_count"].set_focus();
	},

	number_of_equipment_units: function (frm) {
		populateChildTable(
			frm,
			"equipment_required",
			"equipment_table",
			"number_of_equipment_units",
			"equipment_unit",
			"Equipment"
		);
		calculateTotalCost(frm);
	},

	number_of_material_units: function (frm) {
		populateChildTable(
			frm,
			"material_required",
			"material_table",
			"number_of_material_units",
			"material_unit",
			"Raw Material"
		);
		calculateTotalCost(frm);
	},

	number_of_labor_units: function (frm) {
		populateChildTable(
			frm,
			"labor_required",
			"labor_table",
			"number_of_labor_units",
			"labor_unit",
			"Labor"
		);
		calculateTotalCost(frm);
	},

	labor_count: function (frm) {
		if (frm.doc.labor_count && frm.doc.labor_count > 1) {
			calculateTotalCost(frm);
		}
	},

	material_count: function (frm) {
		if (frm.doc.material_count && frm.doc.material_count > 1) {
			calculateTotalCost(frm);
		}
	},

	equipment_count: function (frm) {
		if (frm.doc.equipment_count && frm.doc.equipment_count > 1) {
			calculateTotalCost(frm);
		}
	},

	before_save: function (frm) {
		// Calculate the final total cost
		calculateTotalCost(frm);

		// Check if this is initial save (not submitted) and total cost exceeds balance
		if (
			frm.is_new() &&
			frm.doc.monthly_maintenance_budget > 0 &&
			frm.doc.total_cost > frm.doc.maintenance_balance
		) {
			return new Promise((resolve, reject) => {
				frappe.confirm(
					"This work amount <strong>exceeds the Maintenance balance</strong> Do you still want to save this work?",
					() => {
						// If user clicks "Yes"
						updateItemNamesWithCount(frm, "equipment_table", "item_display_name", "equipment_count");
						updateItemNamesWithCount(frm, "material_table", "item_display_name", "material_count");
						updateItemNamesWithCount(frm, "labor_table", "item_display_name", "labor_count");
						resolve();
					},
					() => {
						// If user clicks "No"
						reject();
					}
				);
			});
		} else {
			// If total cost doesn't exceed balance or not initial save, just update the item names
			updateItemNamesWithCount(frm, "equipment_table", "item_display_name", "equipment_count");
			updateItemNamesWithCount(frm, "material_table", "item_display_name", "material_count");
			updateItemNamesWithCount(frm, "labor_table", "item_display_name", "labor_count");
		}
	},
});

// ============ ML ANALYTICS FUNCTIONS ============

function getMLPrediction(frm) {
	if (!frm.doc.work_type_name || !frm.doc.plot) {
		frappe.msgprint({
			title: __('Missing Information'),
			indicator: 'orange',
			message: __('Please select both Work Type and Plot to get ML predictions.')
		});
		return;
	}

	frappe.call({
		method: 'managefarmspro.managefarmspro.ml_analytics.dashboard_api.get_cost_prediction_for_work',
		args: {
			work_type_name: frm.doc.work_type_name,
			plot: frm.doc.plot
		},
		freeze: true,
		freeze_message: __('Getting ML Prediction...'),
		callback: function(r) {
			if (r.message) {
				showPredictionDialog(frm, r.message);
			}
		}
	});
}

function showPredictionDialog(frm, prediction) {
	const resources = prediction.resources || {};
	const confidenceBadge = resources.confidence === 'high' 
		? '<span class="badge badge-success">High Confidence</span>'
		: '<span class="badge badge-warning">Low Confidence</span>';
	
	const fallbackNote = prediction.fallback 
		? '<p class="text-muted"><small><i class="fa fa-info-circle"></i> Using historical average (ML models need training)</small></p>'
		: '<p class="text-success"><small><i class="fa fa-check-circle"></i> ML Model Prediction</small></p>';

	let dialog = new frappe.ui.Dialog({
		title: '🔮 ML Cost & Resource Prediction',
		fields: [
			{
				fieldtype: 'HTML',
				fieldname: 'prediction_html',
				options: `
					<div class="prediction-container" style="padding: 15px;">
						<div class="row">
							<div class="col-md-6">
								<div class="card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px;">
									<h3 style="margin: 0; font-size: 28px;">₹${Math.round(prediction.predicted_cost).toLocaleString()}</h3>
									<p style="margin: 5px 0 0 0; opacity: 0.9;">Predicted Cost</p>
								</div>
							</div>
							<div class="col-md-6">
								<div class="card" style="background: #f8f9fa; padding: 20px; border-radius: 10px;">
									${fallbackNote}
									${confidenceBadge}
								</div>
							</div>
						</div>
						
						<div class="mt-4">
							<h5><i class="fa fa-users"></i> Predicted Resources</h5>
							<table class="table table-bordered">
								<tr>
									<td><i class="fa fa-user-friends text-primary"></i> Labor</td>
									<td><strong>${resources.predicted_labor || '-'}</strong> workers</td>
								</tr>
								<tr>
									<td><i class="fa fa-tractor text-success"></i> Equipment</td>
									<td><strong>${resources.predicted_equipment || '-'}</strong> units</td>
								</tr>
								<tr>
									<td><i class="fa fa-boxes text-warning"></i> Materials</td>
									<td><strong>${resources.predicted_material || '-'}</strong> items</td>
								</tr>
							</table>
						</div>
						
						<div class="alert alert-info mt-3">
							<i class="fa fa-lightbulb"></i> 
							<strong>Tip:</strong> These predictions are based on historical data. 
							Actual costs may vary based on specific requirements.
						</div>
					</div>
				`
			}
		],
		primary_action_label: __('Use Prediction'),
		primary_action: function() {
			frappe.show_alert({
				message: __('Prediction noted! Add resources as needed.'),
				indicator: 'green'
			});
			dialog.hide();
		},
		secondary_action_label: __('Close'),
		secondary_action: function() {
			dialog.hide();
		}
	});
	
	dialog.show();
}

function checkAnomaly(frm) {
	if (!frm.doc.name) {
		frappe.msgprint(__('Please save the work first'));
		return;
	}

	frappe.call({
		method: 'managefarmspro.managefarmspro.ml_analytics.predictor.check_anomaly',
		args: {
			work_name: frm.doc.name
		},
		freeze: true,
		freeze_message: __('Analyzing work order...'),
		callback: function(r) {
			if (r.message) {
				showAnomalyResult(r.message);
			}
		}
	});
}

function showAnomalyResult(result) {
	const isAnomaly = result.is_anomaly;
	const iconClass = isAnomaly ? 'fa-exclamation-triangle text-danger' : 'fa-check-circle text-success';
	const title = isAnomaly ? '⚠️ Anomaly Detected' : '✅ Normal Work Order';
	const bgClass = isAnomaly ? 'bg-danger' : 'bg-success';
	
	let dialog = new frappe.ui.Dialog({
		title: title,
		fields: [
			{
				fieldtype: 'HTML',
				fieldname: 'anomaly_html',
				options: `
					<div class="anomaly-result" style="padding: 20px; text-align: center;">
						<i class="fa ${iconClass}" style="font-size: 48px; margin-bottom: 15px;"></i>
						<h4>${result.message}</h4>
						<p class="text-muted">Status: <span class="badge ${bgClass}">${result.status.toUpperCase()}</span></p>
						<p>Anomaly Score: ${result.anomaly_score ? result.anomaly_score.toFixed(2) : 'N/A'}</p>
						${isAnomaly ? `
							<div class="alert alert-warning mt-3">
								<i class="fa fa-info-circle"></i>
								This work order has unusual characteristics compared to historical patterns.
								Please review the costs and resources.
							</div>
						` : `
							<div class="alert alert-success mt-3">
								<i class="fa fa-thumbs-up"></i>
								This work order falls within expected parameters.
							</div>
						`}
					</div>
				`
			}
		],
		primary_action_label: __('OK'),
		primary_action: function() {
			dialog.hide();
		}
	});
	
	dialog.show();
}

function showPredictionHint(frm) {
	// Show a subtle hint that ML prediction is available
	if (frm.doc.plot && frm.doc.work_type_name) {
		frappe.show_alert({
			message: __('💡 ML Prediction available! Click "ML Analytics" → "Get ML Prediction"'),
			indicator: 'blue'
		}, 5);
	}
}

// ============ ORIGINAL HELPER FUNCTIONS ============

function hideAllSections(frm) {
	frm.toggle_display("work_details", false);
	frm.toggle_display("equipment_table", false);
	frm.toggle_display("material_table", false);
	frm.toggle_display("labor_table", false);

	frm.toggle_display("equipment_required", false);
	frm.toggle_display("equipment_count", false);
	frm.toggle_display("number_of_equipment_units", false);
	frm.toggle_display("equipment_unit", false);

	frm.toggle_display("material_required", false);
	frm.toggle_display("material_count", false);
	frm.toggle_display("number_of_material_units", false);
	frm.toggle_display("material_unit", false);

	frm.toggle_display("labor_required", false);
	frm.toggle_display("labor_count", false);
	frm.toggle_display("number_of_labor_units", false);
	frm.toggle_display("labor_unit", false);
}

function showEquipmentFields(frm) {
	frm.toggle_display("work_details", true);
	frm.toggle_display("material_required", false);
	frm.toggle_display("material_count", false);
	frm.toggle_display("number_of_material_units", false);
	frm.toggle_display("material_unit", false);
	frm.toggle_display("labor_required", false);
	frm.toggle_display("labor_count", false);
	frm.toggle_display("number_of_labor_units", false);
	frm.toggle_display("labor_unit", false);

	frm.toggle_display("equipment_required", true);
	frm.toggle_display("equipment_count", true);
	frm.toggle_display("number_of_equipment_units", true);
	frm.toggle_display("equipment_unit", true);
}

function showMaterialFields(frm) {
	frm.toggle_display("work_details", true);
	frm.toggle_display("equipment_required", false);
	frm.toggle_display("equipment_count", false);
	frm.toggle_display("number_of_equipment_units", false);
	frm.toggle_display("equipment_unit", false);
	frm.toggle_display("labor_required", false);
	frm.toggle_display("labor_count", false);
	frm.toggle_display("number_of_labor_units", false);
	frm.toggle_display("labor_unit", false);

	frm.toggle_display("material_required", true);
	frm.toggle_display("material_count", true);
	frm.toggle_display("number_of_material_units", true);
	frm.toggle_display("material_unit", true);
}

function showLaborFields(frm) {
	frm.toggle_display("work_details", true);
	frm.toggle_display("equipment_required", false);
	frm.toggle_display("equipment_count", false);
	frm.toggle_display("number_of_equipment_units", false);
	frm.toggle_display("equipment_unit", false);
	frm.toggle_display("material_required", false);
	frm.toggle_display("material_count", false);
	frm.toggle_display("number_of_material_units", false);
	frm.toggle_display("material_unit", false);

	frm.toggle_display("labor_required", true);
	frm.toggle_display("labor_count", true);
	frm.toggle_display("number_of_labor_units", true);
	frm.toggle_display("labor_unit", true);
}

function autoPopulateUnit(frm, item_field, unit_field) {
	frappe.db.get_value("Item", frm.doc[item_field], "stock_uom", function (r) {
		if (r && r.stock_uom) {
			frm.set_value(unit_field, r.stock_uom);
		}
	});
}

function populateChildTable(frm, item_field, table_field, units_field, unit_field, item_group) {
	let item = frm.doc[item_field];
	let units = frm.doc[units_field];
	let unit = frm.doc[unit_field];
	let count = 1;

	// Get the count field value if applicable
	if (table_field === "labor_table") {
		count = frm.doc.labor_count || 1;
	} else if (table_field === "material_table") {
		count = frm.doc.material_count || 1;
	} else if (table_field === "equipment_table") {
		count = frm.doc.equipment_count || 1;
	}

	if (item && units && unit) {
		// Fetch both item price and item name
		frappe.db.get_value("Item", item, ["item_name"], function (item_result) {
			if (item_result && item_result.item_name) {
				let item_name = item_result.item_name;

				// Append count to item name if count > 1
				if (count > 1) {
					item_name = `${count} ${item_name}`;
				}

				// Now fetch the price for the item
				frappe.db.get_value(
					"Item Price",
					{ item_code: item, price_list: "Standard Selling" },
					"price_list_rate",
					function (price_result) {
						if (price_result && price_result.price_list_rate) {
							let unit_price = price_result.price_list_rate;
							let total_price = unit_price * units * count;

							// Add child row to the relevant table
							let child = frm.add_child(table_field);

							if (table_field === "equipment_table") {
								frappe.model.set_value(child.doctype, child.name, "item_name", item_name);
								frappe.model.set_value(child.doctype, child.name, "item_display_name", item_name);
								frappe.model.set_value(child.doctype, child.name, "number_of_equipment_units", units);
								frappe.model.set_value(child.doctype, child.name, "equipment_unit", unit);
							} else if (table_field === "material_table") {
								frappe.model.set_value(child.doctype, child.name, "material_name", item_name);
								frappe.model.set_value(child.doctype, child.name, "item_display_name", item_name);
								frappe.model.set_value(child.doctype, child.name, "number_of_material_units", units);
								frappe.model.set_value(child.doctype, child.name, "material_unit", unit);
							} else if (table_field === "labor_table") {
								frappe.model.set_value(child.doctype, child.name, "labor_name", item_name);
								frappe.model.set_value(child.doctype, child.name, "item_display_name", item_name);
								frappe.model.set_value(child.doctype, child.name, "number_of_labor_units", units);
								frappe.model.set_value(child.doctype, child.name, "labor_unit", unit);
							}

							frappe.model.set_value(child.doctype, child.name, "unit_price", unit_price);
							frappe.model.set_value(child.doctype, child.name, "total_price", total_price);

							// Refresh the child table
							frm.refresh_field(table_field);

							hideWorkDetailsAndShowChildTable(frm, item_field, units_field, unit_field, table_field);
						}
					}
				);
			}
		});
	}
}

function hideWorkDetailsAndShowChildTable(frm, item_field, units_field, unit_field, table_field) {
	frm.toggle_display("work_details", false);
	frm.set_value(item_field, null);
	frm.set_value(units_field, null);
	frm.set_value(unit_field, null);
	frm.set_value("labor_count", null);
	frm.set_value("equipment_count", null);
	frm.set_value("material_count", null);
	frm.toggle_display(table_field, true);
}

function maintainItemNames(frm, table_field, item_name_field, item_field) {
	frm.doc[table_field].forEach(function (row) {
		if (!row[item_name_field]) {
			frappe.model.set_value(row.doctype, row.name, item_name_field, frm.doc[item_field]);
		}
	});
	frm.refresh_field(table_field);
}

function updateItemNamesWithCount(frm, table_field, item_name_field, count_field) {
	if (frm.doc[table_field]) {
		frm.doc[table_field].forEach(function (row) {
			let count = frm.doc[count_field] || 1;
			if (count > 1) {
				let original_name = row[item_name_field].replace(/^[0-9]+\s/, "");
				frappe.model.set_value(row.doctype, row.name, item_name_field, `${count} ${original_name}`);
			}
		});
		frm.refresh_field(table_field);
	}
}

function checkAndShowChildTables(frm) {
	if (frm.doc.equipment_table && frm.doc.equipment_table.length > 0) {
		frm.toggle_display("equipment_table", true);
	}
	if (frm.doc.material_table && frm.doc.material_table.length > 0) {
		frm.toggle_display("material_table", true);
	}
	if (frm.doc.labor_table && frm.doc.labor_table.length > 0) {
		frm.toggle_display("labor_table", true);
	}
}

function calculateTotalCost(frm) {
	let totalCost = 0;

	if (frm.doc.equipment_table) {
		frm.doc.equipment_table.forEach(function (row) {
			totalCost += row.total_price || 0;
		});
	}
	if (frm.doc.material_table) {
		frm.doc.material_table.forEach(function (row) {
			totalCost += row.total_price || 0;
		});
	}
	if (frm.doc.labor_table) {
		frm.doc.labor_table.forEach(function (row) {
			totalCost += row.total_price || 0;
		});
	}

	frm.set_value("total_cost", totalCost);
}
