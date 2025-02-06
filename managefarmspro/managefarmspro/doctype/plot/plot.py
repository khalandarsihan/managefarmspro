import frappe
from frappe.model.document import Document


class Plot(Document):
	def before_save(self):
		# Capture the old cluster value before it's modified during the update
		self.previous_cluster_name = frappe.db.get_value("Plot", self.name, "cluster_name", cache=False)

	def on_update(self):
		# Handle updates to the Plot and corresponding Cluster
		if self.previous_cluster_name and self.previous_cluster_name != self.cluster_name:
			self.remove_from_previous_cluster(self.previous_cluster_name)

		# self.update_owner_plot_list()
		self.update_customer_plot_list()
		self.update_cluster_plots()

		# Fetch work data dynamically, assuming it's passed in self
		if hasattr(self, "work_details"):
			for work in self.work_details:
				self.update_plot_work_details(work)
				self.update_cluster_work_details(work)

	def remove_from_previous_cluster(self, previous_cluster_name):
		try:
			previous_cluster_doc = frappe.get_doc("Cluster", previous_cluster_name)

			# Remove the plot from the previous cluster's child table
			previous_cluster_doc.plots = [
				plot for plot in previous_cluster_doc.plots if plot.plot != self.name
			]
			previous_cluster_doc.save()

		except frappe.DoesNotExistError:
			frappe.msgprint(f"Error: Previous cluster {previous_cluster_name} does not exist.")
			frappe.log_error(
				f"Previous Cluster {previous_cluster_name} not found for Plot {self.name}",
				"Remove from Old Cluster Error",
			)

	# def update_owner_plot_list(self):
	# 	# Update the list of plots for the corresponding Owner
	# 	owner_name = self.owner_name
	# 	if owner_name:
	# 		try:
	# 			owner_doc = frappe.get_doc("Owner", owner_name)
	# 			exists = False
	# 			for plot in owner_doc.plot_list:
	# 				if plot.plot == self.name:
	# 					plot.plot_name = self.plot_name
	# 					plot.plot_area = self.area
	# 					plot.plot_cluster = self.cluster
	# 					exists = True
	# 					break

	# 			if not exists:
	# 				owner_doc.append(
	# 					"plot_list",
	# 					{
	# 						"plot": self.name,
	# 						"plot_name": self.plot_name,
	# 						"plot_area": self.area,
	# 						"cluster": self.cluster,
	# 					},
	# 				)
	# 			owner_doc.save()

	# 		except frappe.DoesNotExistError:
	# 			frappe.log_error(
	# 				f"Owner {owner_name} not found while creating/updating Plot {self.name}",
	# 				"Populate Plot List Error",
	# 			)

	def update_customer_plot_list(self):
		# Update the list of plots for the corresponding Customer
		customer_name = self.customer_name
		if customer_name:
			try:
				customer_doc = frappe.get_doc("Customer", customer_name)
				exists = False
				for plot in customer_doc.plot_list:
					if plot.plot == self.name:
						plot.plot_name = self.plot_name
						plot.plot_area = self.area
						plot.plot_cluster = self.cluster
						exists = True
						break

				if not exists:
					customer_doc.append(
						"plot_list",
						{
							"plot": self.name,
							"plot_name": self.plot_name,
							"plot_area": self.area,
							"cluster": self.cluster,
						},
					)
				customer_doc.save()

			except frappe.DoesNotExistError:
				frappe.log_error(
					f"Customer {customer_name} not found while creating/updating Plot {self.name}",
					"Populate Plot List Error",
				)

	def update_cluster_plots(self):
		# Update the Plots section of the Cluster Doctype
		cluster_name = self.cluster_name
		if cluster_name:
			try:
				cluster_doc = frappe.get_doc("Cluster", cluster_name)
				exists = False
				for plot in cluster_doc.plots:
					if plot.plot == self.name:
						plot.plot_name = self.plot_name
						plot.plot_area = self.area
						plot.units = self.units
						exists = True
						break

				if not exists:
					cluster_doc.append(
						"plots",
						{
							"plot": self.name,
							"plot_name": self.plot_name,
							"plot_area": self.area,
							"units": self.units,
						},
					)

				cluster_doc.save()

			except frappe.DoesNotExistError:
				frappe.msgprint(f"Error: New cluster {cluster_name} does not exist.")
				frappe.log_error(
					f"Cluster {cluster_name} not found while creating/updating Plot {self.name}",
					"Populate Plots Error",
				)

	def update_plot_work_details(self, work_data):
		# This method updates the Work details in the Plot's child table
		exists = False
		for work in self.work_details:  # Assuming work_details is the child table in Plot
			if work.work_id == work_data.work_id:
				# If the work entry already exists in the plot, update it
				work.work_name = work_data.work_name
				work.work_date = work_data.work_date
				work.status = work_data.status
				work.total_cost = work_data.total_cost
				exists = True
				break

		if not exists:
			# Add a new row to the Plot's work child table
			self.append(
				"work_details",
				{
					"work_id": work_data.work_id,
					"work_name": work_data.work_name,
					"work_date": work_data.work_date,
					"status": work_data.status,
					"total_cost": work_data.total_cost,
				},
			)

	def update_cluster_work_details(self, work_data):
		# Update the Work details in the Cluster's child table
		cluster_name = self.cluster_name
		if cluster_name:
			try:
				cluster_doc = frappe.get_doc("Cluster", cluster_name)

				exists = False
				for cluster_work in cluster_doc.table_bcjd:
					if cluster_work.work_id == work_data.work_id:
						# If the work entry already exists in the cluster, update it
						cluster_work.work_name = work_data.work_name
						cluster_work.work_date = work_data.work_date
						cluster_work.status = work_data.status
						cluster_work.total_cost = work_data.total_cost
						exists = True
						break

				if not exists:
					# Add a new row to the Cluster's work child table
					cluster_doc.append(
						"table_bcjd",
						{
							"work_id": work_data.work_id,
							"work_name": work_data.work_name,
							"work_date": work_data.work_date,
							"status": work_data.status,
							"total_cost": work_data.total_cost,
						},
					)
				# Save the Cluster document
				cluster_doc.save()

			except frappe.DoesNotExistError:
				frappe.msgprint(f"Error: Cluster {cluster_name} does not exist.")
				frappe.log_error(
					f"Cluster {cluster_name} not found while updating work details for Plot {self.name}",
					"Update Work Details Error",
				)
    
