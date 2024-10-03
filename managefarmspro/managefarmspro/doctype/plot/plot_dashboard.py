from frappe import _

# def get_data():
#     return {
#         "fieldname": "plot",
#         "non_standard_fieldnames": {
#             "Work": "plot",  # Ensure this is the link field you used in the Work Doctype
#         },
#         "dynamic_links": {},
#         "transactions": [
#             {
#                 "items": [
#                     "Work",  # Link to the Work Doctype
#                 ]
#             }
#         ]
#     }


# def get_data():
#     return {
#         "fieldname": "plot",
#         "non_standard_fieldnames": {
#             "Work": "plot",
#         },
#         "internal_links": {
#             "Work": ["work_activities", "plot"]  # Links Work Doctype to Plot Doctype
#         },
#         "transactions": [
#             {
#                 "label": _("Work Activities"),
#                 "items": ["Work"]
#             }
#         ]
#     }


# from frappe import _

def get_data():
    return {
        "fieldname": "plot",  # The linking field in the Work Doctype
        "non_standard_fieldnames": {
            "Work": "plot",  # Ensures that the 'plot' link field is defined in Work Doctype
        },
        "transactions": [
            {
                "label": _("Work Activities"),
                "items": ["Work"]  # Include all linked Doctypes here
            }
        ]
    }
