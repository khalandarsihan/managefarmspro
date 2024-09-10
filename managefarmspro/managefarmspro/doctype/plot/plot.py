import frappe
from frappe.model.document import Document


class Plot(Document):
	def before_save(self):
		# Capture the old cluster value before it's modified during the update
		self.previous_cluster_name = frappe.db.get_value("Plot", self.name, "cluster_name", cache=False)

	def on_update(self):
		# Log update details
		# frappe.msgprint(f"on_update called for Plot {self.name}")
		# frappe.msgprint(f"Previous cluster: {self.previous_cluster_name}, New cluster: {self.cluster_name}")

		if self.previous_cluster_name and self.previous_cluster_name != self.cluster_name:
			self.remove_from_previous_cluster(self.previous_cluster_name)

		self.update_owner_plot_list()
		self.update_cluster_plots()

	def remove_from_previous_cluster(self, previous_cluster_name):
		try:
			# Fetch the previous cluster document
			previous_cluster_doc = frappe.get_doc("Cluster", previous_cluster_name)

			# Remove the plot from the previous cluster's child table
			previous_cluster_doc.plots = [
				plot for plot in previous_cluster_doc.plots if plot.plot != self.name
			]
			previous_cluster_doc.save()
			# frappe.msgprint(f"Plot {self.name} removed from previous cluster {previous_cluster_name}")

		except frappe.DoesNotExistError:
			frappe.msgprint(f"Error: Previous cluster {previous_cluster_name} does not exist.")
			frappe.log_error(
				f"Previous Cluster {previous_cluster_name} not found for Plot {self.name}",
				"Remove from Old Cluster Error",
			)

	def update_owner_plot_list(self):
		owner_name = self.owner_name
		if owner_name:
			try:
				owner_doc = frappe.get_doc("Owner", owner_name)
				exists = False
				for plot in owner_doc.plot_list:
					if plot.plot == self.name:
						plot.plot_name = self.plot_name
						plot.plot_area = self.area
						plot.plot_cluster = self.cluster
						exists = True
						break

				if not exists:
					owner_doc.append(
						"plot_list",
						{
							"plot": self.name,
							"plot_name": self.plot_name,
							"plot_area": self.area,
							"cluster": self.cluster,
						},
					)
				owner_doc.save()

			except frappe.DoesNotExistError:
				frappe.log_error(
					f"Owner {owner_name} not found while creating/updating Plot {self.name}",
					"Populate Plot List Error",
				)

	def update_cluster_plots(self):
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
				# frappe.msgprint(f"Plot {self.name} added to new cluster {cluster_name}")

				cluster_doc.save()

			except frappe.DoesNotExistError:
				frappe.msgprint(f"Error: New cluster {cluster_name} does not exist.")
				frappe.log_error(
					f"Cluster {cluster_name} not found while creating/updating Plot {self.name}",
					"Populate Plots Error",
				)
