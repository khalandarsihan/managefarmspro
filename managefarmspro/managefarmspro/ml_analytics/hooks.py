# Copyright (c) 2024-2025, FigAi GenAi Solutions and contributors
# ML Analytics Hooks for ManageFarmsPro
# Author: Khalandar Sihan (2303RES181)

import frappe
from frappe import _


def after_work_insert(doc, method):
    """
    Hook called after a new work order is inserted.
    Can be used for real-time predictions and alerts.
    """
    try:
        # Check if we should show budget warning
        if doc.plot and doc.monthly_maintenance_budget:
            from managefarmspro.managefarmspro.ml_analytics.predictor import get_predictor
            
            predictor = get_predictor()
            
            # Get prediction for the work
            work_data = _prepare_work_data(doc)
            predicted_cost = predictor.predict_cost(work_data)
            
            # Check if predicted cost might exceed budget
            if predicted_cost > doc.maintenance_balance:
                frappe.publish_realtime(
                    'budget_warning',
                    {
                        'work': doc.name,
                        'plot': doc.plot,
                        'predicted_cost': predicted_cost,
                        'balance': doc.maintenance_balance,
                        'message': f'Predicted cost (₹{predicted_cost:,.0f}) may exceed available balance (₹{doc.maintenance_balance:,.0f})'
                    },
                    user=frappe.session.user
                )
                
    except Exception as e:
        # Don't break the insert if ML fails
        frappe.log_error(f"ML Analytics hook error: {str(e)}", "after_work_insert")


def on_work_submit(doc, method):
    """
    Hook called when a work order is submitted.
    Updates ML models with new data point and checks for anomalies.
    """
    try:
        from managefarmspro.managefarmspro.ml_analytics.predictor import get_predictor
        
        predictor = get_predictor()
        
        # Check for anomaly
        work_data = _prepare_work_data(doc)
        anomaly_result = predictor.detect_anomaly(work_data)
        
        if anomaly_result.get('is_anomaly'):
            # Log the anomaly
            frappe.log_error(
                f"Anomaly detected in Work {doc.name}: {anomaly_result.get('message')}",
                "ML Anomaly Detection"
            )
            
            # Notify relevant users
            frappe.publish_realtime(
                'anomaly_detected',
                {
                    'work': doc.name,
                    'plot': doc.plot,
                    'cost': doc.total_cost,
                    'message': anomaly_result.get('message'),
                    'score': anomaly_result.get('anomaly_score')
                },
                user=frappe.session.user
            )
            
        # Check if we should trigger model retraining
        _check_retraining_trigger()
        
    except Exception as e:
        # Don't break the submit if ML fails
        frappe.log_error(f"ML Analytics hook error: {str(e)}", "on_work_submit")


def _prepare_work_data(doc):
    """Prepare work data dictionary for ML models"""
    from datetime import datetime
    
    # Get plot details
    plot_doc = frappe.get_doc("Plot", doc.plot) if doc.plot else None
    
    # Count child items
    labor_count = len(doc.labor_table) if doc.labor_table else 0
    equipment_count = len(doc.equipment_table) if doc.equipment_table else 0
    material_count = len(doc.material_table) if doc.material_table else 0
    
    work_date = doc.work_date or datetime.now()
    
    return {
        'work_type_name': doc.work_type_name,
        'plot': doc.plot,
        'plot_area': float(plot_doc.area if plot_doc else 0),
        'cluster': plot_doc.cluster if plot_doc else None,
        'supervision_charge': float(plot_doc.supervision_charge if plot_doc else 0),
        'monthly_maintenance_budget': float(plot_doc.monthly_maintenance_budget if plot_doc else 0),
        'month': work_date.month if hasattr(work_date, 'month') else datetime.now().month,
        'quarter': (work_date.month - 1) // 3 + 1 if hasattr(work_date, 'month') else 1,
        'year': work_date.year if hasattr(work_date, 'year') else datetime.now().year,
        'day_of_week': work_date.weekday() + 1 if hasattr(work_date, 'weekday') else 1,
        'labor_count': labor_count,
        'equipment_count': equipment_count,
        'material_count': material_count,
        'total_cost': float(doc.total_cost or 0)
    }


def _check_retraining_trigger():
    """Check if ML models should be retrained based on data volume"""
    # Get count of works since last training
    last_training = frappe.db.get_single_value("ML Analytics Settings", "last_training_date") or None
    
    if last_training:
        new_works = frappe.db.count(
            "Work",
            filters={
                "docstatus": 1,
                "modified": [">", last_training]
            }
        )
        
        # Retrain if more than 50 new works since last training
        if new_works >= 50:
            frappe.enqueue(
                "managefarmspro.managefarmspro.ml_analytics.scheduler.retrain_models",
                queue="long",
                timeout=600
            )
    else:
        # No training date recorded, check total works
        total_works = frappe.db.count("Work", filters={"docstatus": 1})
        if total_works >= 100:
            frappe.enqueue(
                "managefarmspro.managefarmspro.ml_analytics.scheduler.retrain_models",
                queue="long",
                timeout=600
            )
