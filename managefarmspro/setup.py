# Copyright (c) 2024-2025, FigAi GenAi Solutions and contributors
# Setup module for ManageFarmsPro
# Author: Khalandar Sihan (2303RES181)

import frappe
from frappe import _


def after_install():
    """
    Post-installation setup for ManageFarmsPro.
    Creates necessary configurations and default data.
    """
    print("Setting up ManageFarmsPro with ML Analytics...")
    
    # Create ML Analytics Settings if not exists
    create_ml_settings()
    
    # Create ML models directory
    create_ml_directory()
    
    # Add ML Analytics to workspace
    update_workspace()
    
    print("ManageFarmsPro setup complete!")


def create_ml_settings():
    """Create ML Analytics Settings single doctype if it doesn't exist"""
    try:
        if not frappe.db.exists("DocType", "ML Analytics Settings"):
            # Create the doctype programmatically
            doc = frappe.get_doc({
                "doctype": "DocType",
                "name": "ML Analytics Settings",
                "module": "Managefarmspro",
                "custom": 1,
                "issingle": 1,
                "track_changes": 1,
                "fields": [
                    {
                        "fieldname": "ml_enabled",
                        "fieldtype": "Check",
                        "label": "Enable ML Analytics",
                        "default": "1"
                    },
                    {
                        "fieldname": "last_training_date",
                        "fieldtype": "Datetime",
                        "label": "Last Training Date",
                        "read_only": 1
                    },
                    {
                        "fieldname": "training_samples",
                        "fieldtype": "Int",
                        "label": "Training Samples",
                        "read_only": 1
                    },
                    {
                        "fieldname": "auto_retrain",
                        "fieldtype": "Check",
                        "label": "Auto Retrain Weekly",
                        "default": "1"
                    },
                    {
                        "fieldname": "anomaly_threshold",
                        "fieldtype": "Float",
                        "label": "Anomaly Detection Threshold",
                        "default": "0.1",
                        "description": "Contamination factor for Isolation Forest (0.01 - 0.5)"
                    },
                    {
                        "fieldname": "section_break_1",
                        "fieldtype": "Section Break",
                        "label": "Model Performance"
                    },
                    {
                        "fieldname": "cost_model_r2",
                        "fieldtype": "Percent",
                        "label": "Cost Model R² Score",
                        "read_only": 1
                    },
                    {
                        "fieldname": "cost_model_mae",
                        "fieldtype": "Currency",
                        "label": "Cost Model MAE",
                        "read_only": 1
                    }
                ],
                "permissions": [
                    {
                        "role": "System Manager",
                        "read": 1,
                        "write": 1
                    }
                ]
            })
            doc.insert(ignore_permissions=True)
            print("Created ML Analytics Settings doctype")
    except Exception as e:
        print(f"Note: ML Analytics Settings setup: {str(e)}")


def create_ml_directory():
    """Create directory for ML models"""
    import os
    
    try:
        models_dir = frappe.get_site_path("private", "ml_models")
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)
            print(f"Created ML models directory: {models_dir}")
    except Exception as e:
        print(f"Note: Could not create ML directory: {str(e)}")


def update_workspace():
    """Add ML Analytics Dashboard to workspace"""
    try:
        workspace = frappe.get_doc("Workspace", "ManageFarmsPro")
        
        # Check if shortcut already exists
        shortcut_exists = any(
            s.get("link_to") == "ml-analytics-dashboard" 
            for s in workspace.shortcuts
        )
        
        if not shortcut_exists:
            workspace.append("shortcuts", {
                "label": "ML Analytics",
                "link_to": "ml-analytics-dashboard",
                "type": "Page",
                "color": "Purple",
                "icon": "analytics"
            })
            workspace.save(ignore_permissions=True)
            print("Added ML Analytics to workspace")
            
    except Exception as e:
        print(f"Note: Workspace update: {str(e)}")


def check_ml_dependencies():
    """Check if ML dependencies are installed"""
    dependencies = {
        'sklearn': False,
        'pandas': False,
        'numpy': False
    }
    
    try:
        import sklearn
        dependencies['sklearn'] = True
    except ImportError:
        pass
    
    try:
        import pandas
        dependencies['pandas'] = True
    except ImportError:
        pass
    
    try:
        import numpy
        dependencies['numpy'] = True
    except ImportError:
        pass
    
    return dependencies
