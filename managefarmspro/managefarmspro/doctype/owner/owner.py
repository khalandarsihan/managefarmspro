import frappe
from frappe.model.document import Document

class Owner(Document):
    def before_save(self):
        # Automatically generate full name before saving the document
        self.full_name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        
        # Create or update the customer when the owner is created or modified
        create_or_update_customer_from_owner(self)

# Function to create or update a Customer from Owner
def create_or_update_customer_from_owner(owner_doc):
    # Check if the customer already exists for this owner
    customer = frappe.db.exists("Customer", {"customer_name": owner_doc.full_name})

    if not customer:
        # Create a new Customer
        customer = frappe.new_doc("Customer")

        # Set customer details based on the Owner's information
        customer.customer_name = owner_doc.full_name
        customer.customer_type = "Individual"  # Assuming owners are individuals, change if needed
        customer.territory = "All Territories"  # Set default territory or customize it
        customer.customer_group = "Individual"  # Set the default customer group

        # Set optional fields like email, phone, address
        customer.email_id = owner_doc.email
        customer.mobile_no = owner_doc.phone_number

        # Save the new Customer
        customer.insert()
        frappe.msgprint(f"Customer {customer.customer_name} created successfully from Owner {owner_doc.full_name}")

        # Link the customer to the owner (no need to call save again after this)
        owner_doc.db_set('customer', customer.name)
    else:
        # Update the existing Customer with new information
        customer = frappe.get_doc("Customer", customer)
        customer.customer_name = owner_doc.full_name
        customer.email_id = owner_doc.email
        customer.mobile_no = owner_doc.phone_number

        # Save the updated Customer
        customer.save()
        # frappe.msgprint(f"Customer {customer.customer_name} updated successfully from Owner {owner_doc.full_name}")

    # Optionally create or update the address
    create_or_update_customer_address(owner_doc, customer)

# Function to create or update a Customer's address
def create_or_update_customer_address(owner_doc, customer_doc):
    if owner_doc.address:
        # Check if an address already exists for the customer
        address_exists = frappe.db.exists("Address", {"address_title": owner_doc.full_name})

        if not address_exists:
            # Create a new Address for the customer
            address = frappe.new_doc("Address")
            address.address_title = owner_doc.full_name
            address.address_line1 = owner_doc.address
            address.city = "Unknown"  # Set a default city or customize it
            address.address_type = "Billing"
            address.links = [{
                "link_doctype": "Customer",
                "link_name": customer_doc.name
            }]
            address.insert()
            # frappe.msgprint(f"Address for Customer {customer_doc.customer_name} created successfully.")
        else:
            # Update the existing Address
            address = frappe.get_doc("Address", address_exists)
            address.address_line1 = owner_doc.address
            address.save()
            # frappe.msgprint(f"Address for Customer {customer_doc.customer_name} updated successfully.")
