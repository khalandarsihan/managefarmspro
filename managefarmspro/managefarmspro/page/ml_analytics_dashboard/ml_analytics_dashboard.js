// ML Analytics Dashboard JavaScript
// ManageFarmsPro - Predictive Analytics Module
// Author: Khalandar Sihan (2303RES181)

frappe.pages["ml-analytics-dashboard"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "ML Analytics Dashboard",
		single_column: true,
	});

	new MLAnalyticsDashboard(page);
};

class MLAnalyticsDashboard {
	constructor(page) {
		this.page = page;
		this.charts = {};
		this.data = null;
		this.work_type_field = null;
		this.plot_field = null;
		this.forecast_plot_field = null;

		this.make();
		this.load_data();
	}

	make() {
		this.$container = $(frappe.render_template("ml_analytics_dashboard", {}));
		$(this.page.body).append(this.$container);

		this.setup_actions();
	}

	setup_actions() {
		// Train Models button
		this.$container.find("#train-models-btn").on("click", () => {
			this.train_models();
		});

		// Predict Cost button
		this.$container.find("#predict-cost-btn").on("click", () => {
			this.predict_cost();
		});

		// Generate Forecast button
		this.$container.find("#generate-forecast-btn").on("click", () => {
			this.generate_forecast();
		});

		// Setup link fields
		this.setup_link_fields();
	}

	setup_link_fields() {
		// Work Type field
		this.work_type_field = frappe.ui.form.make_control({
			parent: this.$container.find("#work-type-field"),
			df: {
				fieldtype: "Link",
				options: "Work Item",
				fieldname: "work_type",
				placeholder: "Select Work Type",
			},
			render_input: true,
		});
		this.work_type_field.refresh();

		// Plot field for prediction
		this.plot_field = frappe.ui.form.make_control({
			parent: this.$container.find("#plot-field"),
			df: {
				fieldtype: "Link",
				options: "Plot",
				fieldname: "plot",
				placeholder: "Select Plot",
			},
			render_input: true,
		});
		this.plot_field.refresh();

		// Plot field for forecast
		this.forecast_plot_field = frappe.ui.form.make_control({
			parent: this.$container.find("#forecast-plot-field"),
			df: {
				fieldtype: "Link",
				options: "Plot",
				fieldname: "forecast_plot",
				placeholder: "Select Plot",
			},
			render_input: true,
		});
		this.forecast_plot_field.refresh();
	}

	load_data() {
		frappe.call({
			method: "managefarmspro.managefarmspro.ml_analytics.dashboard_api.get_dashboard_data",
			freeze: true,
			freeze_message: __("Loading Dashboard..."),
			callback: (r) => {
				if (r.message) {
					this.data = r.message;
					console.log("Dashboard data loaded:", this.data);
					this.render_dashboard();
				} else {
					frappe.msgprint(__("Failed to load dashboard data"));
				}
			},
			error: (err) => {
				console.error("Dashboard load error:", err);
				frappe.msgprint(__("Error loading dashboard data"));
			},
		});
	}

	render_dashboard() {
		this.render_summary_cards();
		this.render_model_status();
		this.render_cost_trends_chart();
		this.render_work_distribution_chart();
		this.render_budget_alerts();
		this.render_seasonal_patterns();
		this.render_monthly_spending();
	}

	render_summary_cards() {
		const summary = this.data.summary || {};

		// Works this month
		this.$container.find("#works-this-month").text(summary.works_this_month || 0);
		const worksChange = summary.works_change || 0;
		this.$container
			.find("#works-change")
			.html(
				worksChange >= 0
					? `<span class="text-success">↑ ${worksChange}% vs last month</span>`
					: `<span class="text-danger">↓ ${Math.abs(worksChange)}% vs last month</span>`
			);

		// Total cost
		this.$container
			.find("#total-cost")
			.text(`₹${this.format_number(summary.total_cost || 0)}`);

		// Average cost
		this.$container.find("#avg-cost").text(`₹${this.format_number(summary.avg_cost || 0)}`);

		// Plots over budget
		this.$container.find("#plots-over-budget").text(summary.plots_over_budget || 0);

		// Active plots
		this.$container.find("#active-plots").text(summary.total_plots || 0);
	}

	render_model_status() {
		const status = this.data.model_status || {};
		const $banner = this.$container.find("#model-status-banner");
		const dateRange = status.date_range || "Jan 2025 - Sep 2025";

		if (status.cost_predictor_trained && status.anomaly_detector_trained) {
			$banner.html(`
                <div class="alert alert-success">
                    <i class="fa fa-check-circle"></i>
                    <strong>ML Models Ready</strong> - All prediction models are trained and active.
                    <span class="text-muted ml-3">Training Data: ${
						status.training_data_count || 0
					} records</span>
                    <span class="badge badge-info ml-2">Data: ${dateRange}</span>
                </div>
            `);
		} else {
			$banner.html(`
                <div class="alert alert-warning">
                    <i class="fa fa-exclamation-triangle"></i>
                    <strong>ML Models Not Trained</strong> - Click "Train Models" to enable predictions.
                    <span class="text-muted ml-3">Available Data: ${
						status.training_data_count || 0
					} records (min: ${status.minimum_required || 10})</span>
                    <span class="badge badge-info ml-2">Data: ${dateRange}</span>
                </div>
            `);
		}
	}

	render_cost_trends_chart() {
		const trends = this.data.cost_trends || [];
		const $container = this.$container.find("#cost-trends-chart");

		console.log("Cost trends data:", trends);

		if (!trends || trends.length === 0) {
			$container.html(
				'<div class="text-center text-muted p-4"><i class="fa fa-chart-line fa-2x mb-2"></i><br>No cost data available for the last 12 months</div>'
			);
			return;
		}

		// Clear container and create canvas
		$container.empty();
		const canvas = $('<canvas id="costTrendsCanvas" height="250"></canvas>');
		$container.append(canvas);

		const ctx = canvas[0].getContext("2d");

		// Destroy existing chart if any
		if (this.charts.costTrends) {
			this.charts.costTrends.destroy();
		}

		this.charts.costTrends = new Chart(ctx, {
			type: "line",
			data: {
				labels: trends.map((t) => t.month_label || t.month),
				datasets: [
					{
						label: "Total Cost",
						data: trends.map((t) => parseFloat(t.total_cost) || 0),
						borderColor: "#667eea",
						backgroundColor: "rgba(102, 126, 234, 0.1)",
						fill: true,
						tension: 0.4,
					},
					{
						label: "Work Count",
						data: trends.map((t) => parseInt(t.work_count) || 0),
						borderColor: "#28a745",
						backgroundColor: "transparent",
						yAxisID: "y1",
						tension: 0.4,
					},
				],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				interaction: {
					intersect: false,
					mode: "index",
				},
				scales: {
					y: {
						type: "linear",
						display: true,
						position: "left",
						title: {
							display: true,
							text: "Cost (₹)",
						},
						ticks: {
							callback: (value) => "₹" + this.format_number(value),
						},
					},
					y1: {
						type: "linear",
						display: true,
						position: "right",
						title: {
							display: true,
							text: "Work Count",
						},
						grid: {
							drawOnChartArea: false,
						},
					},
				},
				plugins: {
					legend: {
						position: "top",
					},
					tooltip: {
						callbacks: {
							label: (context) => {
								if (context.datasetIndex === 0) {
									return `Cost: ₹${this.format_number(context.raw)}`;
								}
								return `Works: ${context.raw}`;
							},
						},
					},
				},
			},
		});
	}

	render_work_distribution_chart() {
		const distribution = this.data.work_distribution || [];
		const $container = this.$container.find("#work-distribution-chart");

		console.log("Work distribution data:", distribution);

		if (!distribution || distribution.length === 0) {
			$container.html(
				'<div class="text-center text-muted p-4"><i class="fa fa-pie-chart fa-2x mb-2"></i><br>No work distribution data available</div>'
			);
			return;
		}

		// Clear container and create canvas
		$container.empty();
		const canvas = $('<canvas id="workDistCanvas" height="250"></canvas>');
		$container.append(canvas);

		const ctx = canvas[0].getContext("2d");

		// Generate colors
		const colors = [
			"#667eea",
			"#764ba2",
			"#f093fb",
			"#f5576c",
			"#4facfe",
			"#00f2fe",
			"#43e97b",
			"#38f9d7",
			"#fa709a",
			"#fee140",
		];

		// Destroy existing chart if any
		if (this.charts.workDist) {
			this.charts.workDist.destroy();
		}

		this.charts.workDist = new Chart(ctx, {
			type: "doughnut",
			data: {
				labels: distribution.map((d) => d.work_type_name || "Unknown"),
				datasets: [
					{
						data: distribution.map((d) => parseInt(d.count) || 0),
						backgroundColor: colors.slice(0, distribution.length),
						borderWidth: 2,
						borderColor: "#fff",
					},
				],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: {
						position: "right",
						labels: {
							boxWidth: 12,
							padding: 10,
						},
					},
					tooltip: {
						callbacks: {
							label: (context) => {
								const total = context.dataset.data.reduce((a, b) => a + b, 0);
								const percentage = ((context.raw / total) * 100).toFixed(1);
								return `${context.label}: ${context.raw} (${percentage}%)`;
							},
						},
					},
				},
			},
		});
	}

	render_budget_alerts() {
		const alerts = this.data.budget_alerts || [];
		const $container = this.$container.find("#budget-alerts-container");

		console.log("Budget alerts data:", alerts);

		if (!alerts || alerts.length === 0) {
			$container.html(`
                <div class="text-center text-muted p-4">
                    <i class="fa fa-check-circle fa-2x text-success mb-2"></i><br>
                    No budget alerts - All plots within budget!
                </div>
            `);
			return;
		}

		let html = '<div class="list-group">';
		alerts.forEach((alert) => {
			const badgeClass = alert.severity === "critical" ? "badge-danger" : "badge-warning";
			const bgClass = alert.severity === "critical" ? "bg-danger-light" : "bg-warning-light";
			html += `
                <div class="list-group-item ${bgClass}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${alert.plot_name || alert.plot}</strong>
                            <br><small class="text-muted">${alert.customer || ""}</small>
                        </div>
                        <div class="text-right">
                            <span class="badge ${badgeClass}">${alert.severity.toUpperCase()}</span>
                            <br><small>${alert.message}</small>
                        </div>
                    </div>
                </div>
            `;
		});
		html += "</div>";

		$container.html(html);
	}

	render_seasonal_patterns() {
		const patterns = this.data.seasonal_patterns || {};
		const $container = this.$container.find("#seasonal-patterns-container");

		console.log("Seasonal patterns data:", patterns);

		const months = patterns.months || [];

		if (!months || months.length === 0) {
			$container.html(`
                <div class="text-center text-muted p-4">
                    <i class="fa fa-calendar fa-2x mb-2"></i><br>
                    Insufficient data for seasonal analysis<br>
                    <small>Need at least 24 months of data</small>
                </div>
            `);
			return;
		}

		let html = '<div class="row">';

		// Peak months
		html +=
			'<div class="col-md-6"><h6 class="text-success"><i class="fa fa-arrow-up"></i> Peak Months</h6>';
		if (patterns.peak_months && patterns.peak_months.length > 0) {
			patterns.peak_months.forEach((m) => {
				html += `<span class="badge badge-success mr-1 mb-1">${m}</span>`;
			});
		} else {
			html += '<span class="text-muted">No significant peaks</span>';
		}
		html += "</div>";

		// Low months
		html +=
			'<div class="col-md-6"><h6 class="text-warning"><i class="fa fa-arrow-down"></i> Low Months</h6>';
		if (patterns.low_months && patterns.low_months.length > 0) {
			patterns.low_months.forEach((m) => {
				html += `<span class="badge badge-warning mr-1 mb-1">${m}</span>`;
			});
		} else {
			html += '<span class="text-muted">No significant lows</span>';
		}
		html += "</div>";

		html += "</div>";

		// Monthly breakdown table
		if (months.length > 0) {
			html +=
				'<hr><div class="table-responsive"><table class="table table-sm"><thead><tr><th>Month</th><th>Works</th><th>Avg Cost</th></tr></thead><tbody>';
			months.forEach((m) => {
				html += `<tr>
                    <td>${m.month_name}</td>
                    <td>${m.work_count || 0}</td>
                    <td>₹${this.format_number(m.avg_cost || 0)}</td>
                </tr>`;
			});
			html += "</tbody></table></div>";
		}

		$container.html(html);
	}

	render_monthly_spending() {
		const spending = this.data.monthly_spending || [];
		const $container = this.$container.find("#monthly-spending-table");

		console.log("Monthly spending data:", spending);

		if (!spending || spending.length === 0) {
			$container.html(`
				<div class="text-center text-muted p-4">
					<i class="fa fa-table fa-2x mb-2"></i><br>
					No spending data available for this month
				</div>
			`);
			return;
		}

		let html = `
			<div class="table-responsive">
				<table class="table table-hover">
					<thead>
						<tr>
							<th style="width: 25%;">Plot</th>
							<th style="width: 12%; text-align: right;">Budget</th>
							<th style="width: 12%; text-align: right;">Spent</th>
							<th style="width: 12%; text-align: right;">Balance</th>
							<th style="width: 25%;">Utilization</th>
							<th style="width: 14%; text-align: center;">Status</th>
						</tr>
					</thead>
					<tbody>
		`;

		spending.forEach((s) => {
			const utilization = s.utilization || 0;
			let progressClass = "bg-success";
			let statusBadge = '<span class="badge badge-success">On Track</span>';

			if (utilization > 100) {
				progressClass = "bg-danger";
				statusBadge = '<span class="badge badge-danger">Over Budget</span>';
			} else if (utilization > 80) {
				progressClass = "bg-warning";
				statusBadge = '<span class="badge badge-warning">Near Limit</span>';
			}

			html += `
				<tr>
					<td>
						<a href="/app/plot/${s.plot}">${s.plot_name || s.plot}</a>
						<br><small class="text-muted">${s.customer || ""}</small>
					</td>
					<td style="text-align: right;">₹${this.format_number(s.budget || 0)}</td>
					<td style="text-align: right;">₹${this.format_number(s.spent || 0)}</td>
					<td style="text-align: right;">₹${this.format_number(s.balance || 0)}</td>
					<td>
						<div class="progress" style="height: 20px; min-width: 100px;">
							<div class="progress-bar ${progressClass}" style="width: ${Math.min(utilization, 100)}%">
								${utilization.toFixed(1)}%
							</div>
						</div>
					</td>
					<td style="text-align: center;">${statusBadge}</td>
				</tr>
			`;
		});

		html += `
					</tbody>
				</table>
			</div>
		`;

		$container.html(html);
	}

	train_models() {
		frappe.call({
			method: "managefarmspro.managefarmspro.ml_analytics.predictor.train_models",
			freeze: true,
			freeze_message: __("Training ML Models... This may take a moment."),
			callback: (r) => {
				if (r.message) {
					const result = r.message;
					if (result.success) {
						frappe.msgprint({
							title: __("Models Trained Successfully"),
							indicator: "green",
							message: `
                                <p><strong>Training Complete!</strong></p>
                                <p>Training Samples: ${
									result.metrics?.training_samples || "N/A"
								}</p>
                                <p>Test Samples: ${Math.round(
									(result.metrics?.training_samples || 0) * 0.25
								)}</p>
                                <hr>
                                <p><strong>Cost Prediction Metrics:</strong></p>
                                <ul>
                                    <li>MAE: ₹${result.metrics?.mae || "N/A"}</li>
                                    <li>R² Score: ${(
										(result.metrics?.r2_score || 0) * 100
									).toFixed(1)}%</li>
                                </ul>
                            `,
						});
						this.load_data(); // Refresh dashboard
					} else {
						frappe.msgprint({
							title: __("Training Failed"),
							indicator: "red",
							message: result.message,
						});
					}
				}
			},
			error: (err) => {
				console.error("Training error:", err);
				frappe.msgprint(__("Error training models. Check console for details."));
			},
		});
	}

	predict_cost() {
		const work_type = this.work_type_field ? this.work_type_field.get_value() : null;
		const plot = this.plot_field ? this.plot_field.get_value() : null;

		if (!work_type || !plot) {
			frappe.msgprint(__("Please select both Work Type and Plot"));
			return;
		}

		frappe.call({
			method: "managefarmspro.managefarmspro.ml_analytics.dashboard_api.get_cost_prediction_for_work",
			args: {
				work_type_name: work_type,
				plot: plot,
			},
			freeze: true,
			freeze_message: __("Calculating prediction..."),
			callback: (r) => {
				if (r.message) {
					this.show_prediction_result(r.message);
				}
			},
		});
	}

	show_prediction_result(result) {
		const $container = this.$container.find("#prediction-result");
		const resources = result.resources || {};

		let html = `
            <div class="prediction-result-box p-3 mt-3 rounded" style="background: #f8f9fa; border-left: 4px solid #667eea;">
                <h4 class="mb-2">
                    <i class="fa fa-calculator text-primary"></i> 
                    Predicted Cost: <strong>₹${this.format_number(result.predicted_cost)}</strong>
                </h4>
                <span class="badge ${result.fallback ? "badge-warning" : "badge-success"}">
                    ${result.fallback ? "Historical Average" : "ML Prediction"}
                </span>
                <hr>
                <p class="mb-1"><strong>Predicted Resources:</strong></p>
                <ul class="mb-0">
                    <li><i class="fa fa-users"></i> Labor: ${
						resources.predicted_labor || 1
					} workers</li>
                    <li><i class="fa fa-cog"></i> Equipment: ${
						resources.predicted_equipment || 1
					} units</li>
                    <li><i class="fa fa-box"></i> Materials: ${
						resources.predicted_material || 1
					} items</li>
                </ul>
                <small class="text-muted">Confidence: ${resources.confidence || "N/A"}</small>
            </div>
        `;

		$container.html(html);
	}

	generate_forecast() {
		const plot = this.forecast_plot_field ? this.forecast_plot_field.get_value() : null;

		if (!plot) {
			frappe.msgprint(__("Please select a Plot"));
			return;
		}

		frappe.call({
			method: "managefarmspro.managefarmspro.ml_analytics.predictor.forecast_budget",
			args: {
				plot_name: plot,
				months_ahead: 3,
			},
			freeze: true,
			freeze_message: __("Generating forecast..."),
			callback: (r) => {
				if (r.message) {
					this.show_forecast_result(r.message);
				}
			},
		});
	}

	show_forecast_result(result) {
		const $container = this.$container.find("#forecast-result");

		if (!result.success && result.forecasts?.length === 0) {
			$container.html(`
                <div class="alert alert-warning mt-3">
                    <i class="fa fa-exclamation-triangle"></i>
                    Insufficient historical data for forecasting this plot.
                </div>
            `);
			return;
		}

		// Get plot budget
		frappe.db.get_value("Plot", result.plot, "monthly_maintenance_budget", (r) => {
			const budget = r?.monthly_maintenance_budget || 0;
			const forecasts = result.forecasts || [];
			const avgForecast =
				forecasts.length > 0
					? forecasts.reduce((sum, f) => sum + f.predicted_cost, 0) / forecasts.length
					: 0;
			const trend = avgForecast > result.historical_average ? "increasing" : "decreasing";

			let html = `
                <div class="forecast-result-box p-3 mt-3 rounded" style="background: #f8f9fa; border-left: 4px solid #28a745;">
                    <h5><i class="fa fa-chart-line text-success"></i> Budget Forecast</h5>
                    <p class="mb-1">Current Budget: <strong>₹${this.format_number(
						budget
					)}</strong></p>
                    <p class="mb-1">Historical Average: <strong>₹${this.format_number(
						result.historical_average
					)}</strong></p>
                    <p class="mb-2">Trend: <span class="badge ${
						trend === "increasing" ? "badge-warning" : "badge-success"
					}">${trend}</span></p>
                    <hr>
                    <table class="table table-sm table-bordered mb-0">
                        <thead>
                            <tr>
                                <th>Month</th>
                                <th>Predicted</th>
                                <th>Range</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

			forecasts.forEach((f) => {
				html += `
                    <tr>
                        <td>${f.month_name}</td>
                        <td>₹${this.format_number(f.predicted_cost)}</td>
                        <td>₹${this.format_number(f.confidence_lower)} - ₹${this.format_number(
					f.confidence_upper
				)}</td>
                    </tr>
                `;
			});

			html += `
                        </tbody>
                    </table>
                    ${
						result.note
							? `<small class="text-muted mt-2 d-block">${result.note}</small>`
							: ""
					}
            `;

			// Budget comparison alerts - handle division by zero
			if (budget <= 0 && avgForecast > 0) {
				html += `
                    <div class="alert alert-danger mt-2 mb-0">
                        <i class="fa fa-exclamation-circle"></i>
                        <strong>No budget set!</strong> Predicted spending is ₹${this.format_number(
							avgForecast
						)}/month. Please set a monthly maintenance budget for this plot.
                    </div>
                `;
			} else if (budget > 0 && avgForecast > budget) {
				const percentOfBudget = ((avgForecast / budget) * 100).toFixed(0);
				html += `
                    <div class="alert alert-warning mt-2 mb-0">
                        <i class="fa fa-exclamation-triangle"></i>
                        Predicted spending exceeds budget (${percentOfBudget}% of monthly budget)
                    </div>
                `;
			} else if (budget > 0 && avgForecast > 0) {
				const percentOfBudget = ((avgForecast / budget) * 100).toFixed(0);
				html += `
                    <div class="alert alert-success mt-2 mb-0">
                        <i class="fa fa-check-circle"></i>
                        Budget is appropriately sized for predicted spending (${percentOfBudget}% utilization)
                    </div>
                `;
			}

			html += `</div>`;

			$container.html(html);
		});
	}

	format_number(num) {
		if (num === null || num === undefined) return "0";
		return parseFloat(num).toLocaleString("en-IN", {
			maximumFractionDigits: 0,
		});
	}
}
