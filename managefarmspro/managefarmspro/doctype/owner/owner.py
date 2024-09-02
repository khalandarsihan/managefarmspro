# Copyright (c) 2024, FigAi GenAi Solutions and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Owner(Document):
	def before_save(self):
		# Automatically generate full name before saving the document
		self.full_name = f"{self.first_name or ''} {self.last_name or ''}".strip()
