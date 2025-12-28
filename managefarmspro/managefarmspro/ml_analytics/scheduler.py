# Copyright (c) 2024-2025, FigAi GenAi Solutions and contributors
# ML Analytics Scheduler for ManageFarmsPro
# Author: Khalandar Sihan (2303RES181)

import frappe
from frappe import _
from frappe.utils import now_datetime, add_days, getdate


def daily_model_check():
    """
    Daily check for ML model health and data quality.
    Runs every day to ensure models are performing well.
    """
    try:
        from managefarmspro.managefarmspro.ml_analytics.predictor import get_predictor, ML_AVAILABLE
        
        if not ML_AVAILABLE:
            frappe.log_error("ML Libraries not available for daily check", "ML Scheduler")
            return
        
        predictor = get_predictor()
        
        # Check model status
        models_status = {
            'cost_predictor': predictor.cost_predictor is not None,
            'resource_predictor': predictor.resource_predictor is not None,
            'anomaly_detector': predictor.anomaly_detector is not None
        }
        
        # Log status
        frappe.log_error(
            f"Daily ML Check - Models Status: {models_status}",
            "ML Analytics Daily Check"
        )
        
        # Check for budget alerts
        check_budget_alerts()
        
        # Check for any anomalous patterns in recent works
        check_recent_anomalies()
        
    except Exception as e:
        frappe.log_error(f"Daily model check failed: {str(e)}", "ML Scheduler Error")


def weekly_model_retrain():
    """
    Weekly model retraining to incorporate new data.
    Runs every week to keep models up to date.
    """
    try:
        retrain_models()
    except Exception as e:
        frappe.log_error(f"Weekly model retrain failed: {str(e)}", "ML Scheduler Error")


def monthly_report_generation():
    """
    Monthly ML analytics report generation.
    Creates summary reports of predictions and anomalies.
    """
    try:
        generate_monthly_report()
    except Exception as e:
        frappe.log_error(f"Monthly report generation failed: {str(e)}", "ML Scheduler Error")


def retrain_models():
    """
    Retrain all ML models with latest data.
    """
    from managefarmspro.managefarmspro.ml_analytics.predictor import get_predictor, ML_AVAILABLE
    
    if not ML_AVAILABLE:
        frappe.log_error("ML Libraries not available for retraining", "ML Scheduler")
        return
    
    predictor = get_predictor()
    result = predictor.train_models()
    
    if result.get('success'):
        # Update last training date
        try:
            settings = frappe.get_single("ML Analytics Settings")
            settings.last_training_date = now_datetime()
            settings.training_samples = result.get('training_samples', 0)
            settings.save(ignore_permissions=True)
        except frappe.DoesNotExistError:
            # Create settings if it doesn't exist
            pass
        
        frappe.log_error(
            f"ML Models retrained successfully. Metrics: {result.get('metrics')}",
            "ML Training Success"
        )
    else:
        frappe.log_error(
            f"ML Model retraining failed: {result.get('message')}",
            "ML Training Failed"
        )
    
    return result


def check_budget_alerts():
    """
    Check all plots for budget concerns and send alerts.
    """
    # Get plots with low balance
    low_balance_plots = frappe.db.sql("""
        SELECT 
            name,
            plot_name,
            customer_name,
            monthly_maintenance_budget,
            maintenance_balance,
            total_amount_spent
        FROM `tabPlot`
        WHERE monthly_maintenance_budget > 0
        AND maintenance_balance < monthly_maintenance_budget * 0.2
        ORDER BY maintenance_balance ASC
    """, as_dict=True)
    
    for plot in low_balance_plots:
        # Calculate percentage remaining
        pct_remaining = (plot.maintenance_balance / plot.monthly_maintenance_budget * 100) if plot.monthly_maintenance_budget else 0
        
        # Create notification for critical cases
        if pct_remaining < 10:
            try:
                frappe.get_doc({
                    "doctype": "Notification Log",
                    "subject": f"Critical: Plot {plot.plot_name} budget nearly exhausted",
                    "email_content": f"""
                        <p>Plot <strong>{plot.plot_name}</strong> has only {pct_remaining:.1f}% budget remaining.</p>
                        <p>Budget: ₹{plot.monthly_maintenance_budget:,.2f}</p>
                        <p>Spent: ₹{plot.total_amount_spent:,.2f}</p>
                        <p>Remaining: ₹{plot.maintenance_balance:,.2f}</p>
                    """,
                    "for_user": frappe.get_value("User", {"role_profile_name": "System Manager"}, "name") or "Administrator",
                    "type": "Alert"
                }).insert(ignore_permissions=True)
            except Exception:
                pass  # Ignore notification errors


def check_recent_anomalies():
    """
    Check recent work orders for anomalies.
    """
    from managefarmspro.managefarmspro.ml_analytics.predictor import check_anomaly, ML_AVAILABLE
    
    if not ML_AVAILABLE:
        return
    
    # Get works from the last 7 days
    recent_works = frappe.get_all(
        "Work",
        filters={
            "docstatus": 1,
            "work_date": [">=", add_days(getdate(), -7)]
        },
        fields=["name"],
        limit=50
    )
    
    anomalies = []
    for work in recent_works:
        try:
            result = check_anomaly(work.name)
            if result.get('is_anomaly'):
                anomalies.append({
                    'work': work.name,
                    'message': result.get('message'),
                    'score': result.get('anomaly_score')
                })
        except Exception:
            pass
    
    if anomalies:
        frappe.log_error(
            f"Found {len(anomalies)} anomalies in recent works: {anomalies}",
            "ML Anomaly Alert"
        )


def generate_monthly_report():
    """
    Generate monthly ML analytics report.
    """
    from frappe.utils import get_first_day, get_last_day, add_months
    
    # Get last month's date range
    today = getdate()
    last_month_start = get_first_day(add_months(today, -1))
    last_month_end = get_last_day(add_months(today, -1))
    
    # Gather statistics
    stats = {
        'period_start': str(last_month_start),
        'period_end': str(last_month_end),
        'total_works': frappe.db.count(
            "Work",
            filters={
                "docstatus": 1,
                "work_date": ["between", [last_month_start, last_month_end]]
            }
        ),
        'total_cost': frappe.db.sql("""
            SELECT COALESCE(SUM(total_cost), 0)
            FROM `tabWork`
            WHERE docstatus = 1
            AND work_date BETWEEN %s AND %s
        """, (last_month_start, last_month_end))[0][0],
        'plots_over_budget': frappe.db.count(
            "Plot",
            filters={
                "monthly_maintenance_budget": [">", 0],
                "maintenance_balance": ["<", 0]
            }
        )
    }
    
    # Store report
    try:
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": "Module Def",
            "reference_name": "Managefarmspro",
            "content": f"Monthly ML Analytics Report: {stats}"
        }).insert(ignore_permissions=True)
    except Exception:
        pass
    
    frappe.log_error(
        f"Monthly ML Analytics Report Generated: {stats}",
        "ML Monthly Report"
    )
    
    return stats


@frappe.whitelist()
def trigger_model_training():
    """
    Manually trigger model training.
    Can be called from UI or API.
    """
    frappe.enqueue(
        retrain_models,
        queue="long",
        timeout=600
    )
    return {"status": "Training queued"}


@frappe.whitelist()
def get_scheduler_status():
    """
    Get status of ML scheduler tasks.
    """
    try:
        settings = frappe.get_single("ML Analytics Settings")
        last_training = settings.last_training_date
        training_samples = settings.training_samples
    except frappe.DoesNotExistError:
        last_training = None
        training_samples = 0
    
    return {
        "last_training": last_training,
        "training_samples": training_samples,
        "total_works": frappe.db.count("Work", filters={"docstatus": 1}),
        "works_since_training": frappe.db.count(
            "Work",
            filters={
                "docstatus": 1,
                "modified": [">", last_training]
            }
        ) if last_training else 0
    }
