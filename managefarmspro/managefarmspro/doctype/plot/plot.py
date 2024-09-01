# Copyright (c) 2024, FigAi GenAi Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Plot(Document):
    def after_insert(self):
        # Handle updating the Owner's plot_list
        owner_name = self.owner_name
        if owner_name:
            try:
                owner_doc = frappe.get_doc('Owner', owner_name)

                # Check if the plot already exists in the plot_list to avoid duplication
                exists = False
                for plot in owner_doc.plot_list:
                    if plot.plot == self.name:
                        exists = True
                        break

                if not exists:
                    # Add the new plot to the plot_list child table in the Owner document
                    owner_doc.append('plot_list', {
                        'plot': self.name,
                        'plot_name': self.plot_name,
                        'plot_area': self.area
                    })

                    # Save the Owner document to apply changes
                    owner_doc.save()

            except frappe.DoesNotExistError:
                frappe.log_error(f'Owner {owner_name} not found while creating Plot {self.name}', 'Populate Plot List Error')

        # Handle updating the Cluster's plots table
        cluster_name = self.cluster_name
        if cluster_name:
            try:
                cluster_doc = frappe.get_doc('Cluster', cluster_name)

                # Check if the plot already exists in the plots child table to avoid duplication
                exists = False
                for plot in cluster_doc.plots:
                    if plot.plot == self.name:
                        exists = True
                        break

                if not exists:
                    # Add the new plot to the plots child table in the Cluster document
                    cluster_doc.append('plots', {
                        'plot': self.name,
                        'plot_name': self.plot_name,
                        'plot_area': self.area,
                        'units': self.units
                    })

                    # Save the Cluster document to apply changes
                    cluster_doc.save()

            except frappe.DoesNotExistError:
                frappe.log_error(f'Cluster {cluster_name} not found while creating Plot {self.name}', 'Populate Plots Error')

        # Commit the transaction to the database
        frappe.db.commit()
