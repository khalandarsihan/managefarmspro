# Copyright (c) 2024-2025, FigAi GenAi Solutions and contributors
# ML Analytics Dashboard API for ManageFarmsPro
# Author: Khalandar Sihan (2303RES181)

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months, now_datetime
from datetime import datetime, timedelta

# Try to import ML libraries
try:
    import pandas as pd
    import numpy as np
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    pd = None
    np = None

# ============ DATE RANGE CONFIGURATION ============
# Set the date range for demo/project work data
DATA_START_DATE = '2025-01-01'
DATA_END_DATE = '2025-09-30'
CURRENT_MONTH_START = '2025-09-01'  # Simulated "current month"
LAST_MONTH_START = '2025-08-01'
LAST_MONTH_END = '2025-08-31'
# ==================================================


@frappe.whitelist()
def get_dashboard_data():
    """Get comprehensive dashboard data for ML Analytics"""
    
    data = {
        'summary': get_summary_stats(),
        'cost_trends': get_cost_trends(),
        'work_distribution': get_work_distribution(),
        'budget_alerts': get_budget_alerts(),
        'seasonal_patterns': get_seasonal_patterns(),
        'monthly_spending': get_monthly_spending_by_plot(),
        'model_status': get_model_status()
    }
    
    return data


def get_summary_stats():
    """Get summary statistics for dashboard cards"""
    
    # Total works in "current month" (September 2025)
    works_this_month = frappe.db.count(
        "Work",
        filters={
            "docstatus": 1,
            "work_date": [">=", CURRENT_MONTH_START],
            "work_date": ["<=", DATA_END_DATE]
        }
    )
    
    # If no works in Sep, count Aug as "this month" for demo
    if works_this_month == 0:
        works_this_month = frappe.db.count(
            "Work",
            filters={
                "docstatus": 1,
                "work_date": ["between", [LAST_MONTH_START, LAST_MONTH_END]]
            }
        )
    
    # Total cost in the date range
    total_cost_result = frappe.db.sql("""
        SELECT COALESCE(SUM(total_cost), 0) as total
        FROM `tabWork`
        WHERE docstatus = 1
        AND work_date BETWEEN %s AND %s
    """, (DATA_START_DATE, DATA_END_DATE), as_dict=True)
    
    total_cost = float(total_cost_result[0]['total']) if total_cost_result else 0
    
    # Plots over budget or low balance
    plots_over_budget = frappe.db.count(
        "Plot",
        filters={
            "monthly_maintenance_budget": [">", 0],
            "maintenance_balance": ["<", 0]
        }
    )
    
    # Low balance plots (< 20% remaining)
    low_balance_plots = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabPlot`
        WHERE monthly_maintenance_budget > 0
        AND maintenance_balance >= 0
        AND maintenance_balance < monthly_maintenance_budget * 0.2
    """, as_dict=True)
    
    low_balance_count = plots_over_budget + (low_balance_plots[0]['count'] if low_balance_plots else 0)
    
    # Average work cost (within date range)
    avg_cost_result = frappe.db.sql("""
        SELECT COALESCE(AVG(total_cost), 0) as avg_cost
        FROM `tabWork`
        WHERE docstatus = 1
        AND total_cost > 0
        AND work_date BETWEEN %s AND %s
    """, (DATA_START_DATE, DATA_END_DATE), as_dict=True)
    
    avg_cost = float(avg_cost_result[0]['avg_cost']) if avg_cost_result else 0
    
    # Compare months (Aug vs Jul for demo)
    aug_result = frappe.db.sql("""
        SELECT 
            COUNT(*) as works,
            COALESCE(SUM(total_cost), 0) as total
        FROM `tabWork`
        WHERE docstatus = 1
        AND work_date BETWEEN '2025-08-01' AND '2025-08-31'
    """, as_dict=True)
    
    jul_result = frappe.db.sql("""
        SELECT 
            COUNT(*) as works,
            COALESCE(SUM(total_cost), 0) as total
        FROM `tabWork`
        WHERE docstatus = 1
        AND work_date BETWEEN '2025-07-01' AND '2025-07-31'
    """, as_dict=True)
    
    aug_works = aug_result[0]['works'] if aug_result else 0
    aug_cost = float(aug_result[0]['total']) if aug_result else 0
    jul_works = jul_result[0]['works'] if jul_result else 0
    jul_cost = float(jul_result[0]['total']) if jul_result else 0
    
    # Calculate change percentages
    if jul_works > 0:
        works_change = ((aug_works - jul_works) / jul_works * 100)
    else:
        works_change = 0 if aug_works == 0 else 100
        
    if jul_cost > 0:
        cost_change = ((aug_cost - jul_cost) / jul_cost * 100)
    else:
        cost_change = 0 if aug_cost == 0 else 100
    
    return {
        'works_this_month': works_this_month,
        'works_change': round(works_change, 1),
        'total_cost': round(total_cost, 2),
        'cost_change': round(cost_change, 1),
        'plots_over_budget': low_balance_count,
        'avg_cost': round(avg_cost, 2),
        'total_plots': frappe.db.count("Plot"),
        'total_works': frappe.db.count("Work", filters={
            "docstatus": 1,
            "work_date": ["between", [DATA_START_DATE, DATA_END_DATE]]
        })
    }


def get_cost_trends():
    """Get cost trends from Jan 2025 to Sep 2025"""
    
    trends = frappe.db.sql("""
        SELECT 
            DATE_FORMAT(work_date, '%%Y-%%m') as month,
            DATE_FORMAT(work_date, '%%b %%Y') as month_label,
            SUM(total_cost) as total_cost,
            COUNT(*) as work_count,
            AVG(total_cost) as avg_cost
        FROM `tabWork`
        WHERE docstatus = 1
        AND work_date BETWEEN %s AND %s
        AND total_cost > 0
        GROUP BY DATE_FORMAT(work_date, '%%Y-%%m')
        ORDER BY month
    """, (DATA_START_DATE, DATA_END_DATE), as_dict=True)
    
    # Convert to regular dict and ensure numeric types
    result = []
    for t in trends:
        result.append({
            'month': t.get('month'),
            'month_label': t.get('month_label'),
            'total_cost': float(t.get('total_cost') or 0),
            'work_count': int(t.get('work_count') or 0),
            'avg_cost': float(t.get('avg_cost') or 0)
        })
    
    return result


def get_work_distribution():
    """Get work distribution by type (Jan 2025 - Sep 2025)"""
    
    distribution = frappe.db.sql("""
        SELECT 
            work_type_name,
            COUNT(*) as count,
            SUM(total_cost) as total_cost,
            AVG(total_cost) as avg_cost
        FROM `tabWork`
        WHERE docstatus = 1
        AND total_cost > 0
        AND work_date BETWEEN %s AND %s
        GROUP BY work_type_name
        ORDER BY count DESC
        LIMIT 10
    """, (DATA_START_DATE, DATA_END_DATE), as_dict=True)
    
    # Convert to regular dict and ensure numeric types
    result = []
    for d in distribution:
        result.append({
            'work_type_name': d.get('work_type_name') or 'Unknown',
            'count': int(d.get('count') or 0),
            'total_cost': float(d.get('total_cost') or 0),
            'avg_cost': float(d.get('avg_cost') or 0)
        })
    
    return result


def get_budget_alerts():
    """Get budget alerts for plots"""
    
    alerts = []
    
    # Plots over budget
    over_budget = frappe.db.sql("""
        SELECT 
            name,
            plot_name,
            customer_name,
            monthly_maintenance_budget,
            maintenance_balance,
            total_amount_spent
        FROM `tabPlot`
        WHERE monthly_maintenance_budget > 0
        AND maintenance_balance < 0
        ORDER BY maintenance_balance ASC
        LIMIT 10
    """, as_dict=True)
    
    for plot in over_budget:
        alerts.append({
            'plot': plot.get('name'),
            'plot_name': plot.get('plot_name'),
            'customer': plot.get('customer_name'),
            'budget': float(plot.get('monthly_maintenance_budget') or 0),
            'spent': float(plot.get('total_amount_spent') or 0),
            'balance': float(plot.get('maintenance_balance') or 0),
            'severity': 'critical',
            'message': f"Over budget by ₹{abs(float(plot.get('maintenance_balance') or 0)):,.2f}"
        })
    
    # Plots nearing budget (>80% used)
    near_budget = frappe.db.sql("""
        SELECT 
            name,
            plot_name,
            customer_name,
            monthly_maintenance_budget,
            maintenance_balance,
            total_amount_spent
        FROM `tabPlot`
        WHERE monthly_maintenance_budget > 0
        AND maintenance_balance >= 0
        AND maintenance_balance < monthly_maintenance_budget * 0.2
        ORDER BY maintenance_balance ASC
        LIMIT 10
    """, as_dict=True)
    
    for plot in near_budget:
        budget = float(plot.get('monthly_maintenance_budget') or 1)
        balance = float(plot.get('maintenance_balance') or 0)
        pct_used = (1 - balance / budget) * 100 if budget > 0 else 0
        
        alerts.append({
            'plot': plot.get('name'),
            'plot_name': plot.get('plot_name'),
            'customer': plot.get('customer_name'),
            'budget': budget,
            'spent': float(plot.get('total_amount_spent') or 0),
            'balance': balance,
            'severity': 'warning',
            'message': f"{pct_used:.1f}% budget used"
        })
    
    return alerts


def get_seasonal_patterns():
    """Analyze seasonal patterns in work orders (Jan 2025 - Sep 2025)"""
    
    patterns = frappe.db.sql("""
        SELECT 
            MONTH(work_date) as month_num,
            MONTHNAME(work_date) as month_name,
            COUNT(*) as work_count,
            SUM(total_cost) as total_cost,
            AVG(total_cost) as avg_cost
        FROM `tabWork`
        WHERE docstatus = 1
        AND total_cost > 0
        AND work_date BETWEEN %s AND %s
        GROUP BY MONTH(work_date), MONTHNAME(work_date)
        ORDER BY month_num
    """, (DATA_START_DATE, DATA_END_DATE), as_dict=True)
    
    if not patterns:
        return {'months': [], 'peak_months': [], 'low_months': []}
    
    # Convert to regular dict
    patterns_list = []
    for p in patterns:
        patterns_list.append({
            'month_num': int(p.get('month_num') or 0),
            'month_name': p.get('month_name') or '',
            'work_count': int(p.get('work_count') or 0),
            'total_cost': float(p.get('total_cost') or 0),
            'avg_cost': float(p.get('avg_cost') or 0)
        })
    
    # Find peak and low months
    peak_months = []
    low_months = []
    
    if patterns_list:
        avg_count = sum(p['work_count'] for p in patterns_list) / len(patterns_list)
        peak_months = [p['month_name'] for p in patterns_list if p['work_count'] > avg_count * 1.2]
        low_months = [p['month_name'] for p in patterns_list if p['work_count'] < avg_count * 0.8]
    
    return {
        'months': patterns_list,
        'peak_months': peak_months,
        'low_months': low_months
    }


def get_monthly_spending_by_plot():
    """Get spending breakdown by plot (Jan 2025 - Sep 2025)"""
    
    # Get plots with budget and their spending in the date range
    spending = frappe.db.sql("""
        SELECT 
            p.name as plot,
            p.plot_name,
            p.customer_name,
            p.monthly_maintenance_budget as budget,
            p.maintenance_balance as balance,
            COALESCE((
                SELECT SUM(w.total_cost) 
                FROM `tabWork` w 
                WHERE w.plot = p.name 
                AND w.docstatus = 1
                AND w.work_date BETWEEN %s AND %s
            ), 0) as spent_in_period,
            COALESCE((
                SELECT COUNT(*) 
                FROM `tabWork` w 
                WHERE w.plot = p.name 
                AND w.docstatus = 1
                AND w.work_date BETWEEN %s AND %s
            ), 0) as work_count
        FROM `tabPlot` p
        WHERE p.monthly_maintenance_budget > 0
        ORDER BY spent_in_period DESC
        LIMIT 20
    """, (DATA_START_DATE, DATA_END_DATE, DATA_START_DATE, DATA_END_DATE), as_dict=True)
    
    result = []
    for s in spending:
        budget = float(s.get('budget') or 0)
        spent = float(s.get('spent_in_period') or 0)
        # Calculate utilization based on 9 months of budget (Jan-Sep)
        nine_month_budget = budget * 9
        utilization = (spent / nine_month_budget * 100) if nine_month_budget > 0 else 0
        
        result.append({
            'plot': s.get('plot'),
            'plot_name': s.get('plot_name'),
            'customer': s.get('customer_name'),
            'budget': budget,
            'spent': spent,
            'balance': float(s.get('balance') or 0),
            'utilization': round(utilization, 1),
            'works': int(s.get('work_count') or 0)
        })
    
    return result


def get_model_status():
    """Get ML model training status"""
    from managefarmspro.managefarmspro.ml_analytics.predictor import get_predictor, ML_AVAILABLE
    
    predictor = get_predictor()
    
    # Count works in the date range
    training_data_count = frappe.db.count("Work", filters={
        "docstatus": 1,
        "work_date": ["between", [DATA_START_DATE, DATA_END_DATE]]
    })
    
    return {
        'ml_available': ML_AVAILABLE,
        'cost_predictor_trained': predictor.cost_predictor is not None,
        'resource_predictor_trained': predictor.resource_predictor is not None,
        'anomaly_detector_trained': predictor.anomaly_detector is not None,
        'training_data_count': training_data_count,
        'minimum_required': 10,
        'date_range': f"{DATA_START_DATE} to {DATA_END_DATE}"
    }


@frappe.whitelist()
def get_plot_analytics(plot_name):
    """Get detailed analytics for a specific plot (Jan 2025 - Sep 2025)"""
    
    plot = frappe.get_doc("Plot", plot_name)
    
    # Historical spending in the date range
    historical = frappe.db.sql("""
        SELECT 
            DATE_FORMAT(work_date, '%%Y-%%m') as month,
            DATE_FORMAT(work_date, '%%b %%Y') as month_label,
            SUM(total_cost) as total_cost,
            COUNT(*) as work_count
        FROM `tabWork`
        WHERE docstatus = 1
        AND plot = %s
        AND work_date BETWEEN %s AND %s
        GROUP BY DATE_FORMAT(work_date, '%%Y-%%m')
        ORDER BY month
    """, (plot_name, DATA_START_DATE, DATA_END_DATE), as_dict=True)
    
    # Work type breakdown
    work_types = frappe.db.sql("""
        SELECT 
            work_type_name,
            COUNT(*) as count,
            SUM(total_cost) as total_cost
        FROM `tabWork`
        WHERE docstatus = 1
        AND plot = %s
        AND work_date BETWEEN %s AND %s
        GROUP BY work_type_name
        ORDER BY total_cost DESC
    """, (plot_name, DATA_START_DATE, DATA_END_DATE), as_dict=True)
    
    # Get forecast
    from managefarmspro.managefarmspro.ml_analytics.predictor import get_predictor
    predictor = get_predictor()
    forecast = predictor.forecast_budget(plot_name, 3)
    
    return {
        'plot': {
            'name': plot.name,
            'plot_name': plot.plot_name,
            'customer': plot.customer_name,
            'area': float(plot.area or 0),
            'budget': float(plot.monthly_maintenance_budget or 0),
            'balance': float(plot.maintenance_balance or 0),
            'total_spent': float(plot.total_amount_spent or 0)
        },
        'historical': [{
            'month': h.get('month'),
            'month_label': h.get('month_label'),
            'total_cost': float(h.get('total_cost') or 0),
            'work_count': int(h.get('work_count') or 0)
        } for h in historical],
        'work_types': [{
            'work_type_name': w.get('work_type_name'),
            'count': int(w.get('count') or 0),
            'total_cost': float(w.get('total_cost') or 0)
        } for w in work_types],
        'forecast': forecast,
        'date_range': f"{DATA_START_DATE} to {DATA_END_DATE}"
    }


@frappe.whitelist()
def get_cost_prediction_for_work(work_type_name, plot):
    """Get cost prediction when creating a new work order"""
    from managefarmspro.managefarmspro.ml_analytics.predictor import get_predictor
    
    predictor = get_predictor()
    
    work_data = {
        'work_type_name': work_type_name,
        'plot': plot,
        'labor_count': 1,
        'equipment_count': 1,
        'material_count': 1
    }
    
    predicted_cost = predictor.predict_cost(work_data)
    predicted_resources = predictor.predict_resources(work_data)
    
    # Get historical context from the date range
    historical = frappe.db.sql("""
        SELECT 
            AVG(total_cost) as avg_cost,
            MIN(total_cost) as min_cost,
            MAX(total_cost) as max_cost,
            COUNT(*) as count
        FROM `tabWork`
        WHERE docstatus = 1
        AND work_type_name = %s
        AND plot = %s
        AND total_cost > 0
        AND work_date BETWEEN %s AND %s
    """, (work_type_name, plot, DATA_START_DATE, DATA_END_DATE), as_dict=True)
    
    context = {}
    if historical and historical[0].get('count', 0) > 0:
        context = {
            'historical_avg': float(historical[0].get('avg_cost') or 0),
            'historical_min': float(historical[0].get('min_cost') or 0),
            'historical_max': float(historical[0].get('max_cost') or 0),
            'historical_count': int(historical[0].get('count') or 0)
        }
    
    return {
        'predicted_cost': round(predicted_cost, 2),
        'resources': predicted_resources,
        'historical_context': context,
        'fallback': predictor.cost_predictor is None
    }


@frappe.whitelist()
def get_anomaly_report():
    """Get report of anomalous work orders (Jan 2025 - Sep 2025)"""
    from managefarmspro.managefarmspro.ml_analytics.predictor import get_predictor
    
    predictor = get_predictor()
    
    # Get works in the date range
    recent_works = frappe.db.sql("""
        SELECT 
            w.name,
            w.work_type_name,
            w.plot,
            w.work_date,
            w.total_cost,
            w.customer,
            (SELECT COUNT(*) FROM `tabLabor Child` lc WHERE lc.parent = w.name) as labor_count,
            (SELECT COUNT(*) FROM `tabEquipment Child` ec WHERE ec.parent = w.name) as equipment_count,
            (SELECT COUNT(*) FROM `tabMaterial Child` mc WHERE mc.parent = w.name) as material_count
        FROM `tabWork` w
        WHERE w.docstatus = 1
        AND w.work_date BETWEEN %s AND %s
        ORDER BY w.work_date DESC
        LIMIT 50
    """, (DATA_START_DATE, DATA_END_DATE), as_dict=True)
    
    anomalies = []
    for work in recent_works:
        work_data = {
            'name': work.get('name'),
            'work_type_name': work.get('work_type_name'),
            'plot': work.get('plot'),
            'work_date': work.get('work_date'),
            'total_cost': float(work.get('total_cost') or 0),
            'labor_count': int(work.get('labor_count') or 0),
            'equipment_count': int(work.get('equipment_count') or 0),
            'material_count': int(work.get('material_count') or 0)
        }
        
        result = predictor.detect_anomaly(work_data)
        
        if result.get('is_anomaly'):
            anomalies.append({
                'work': work.get('name'),
                'work_type': work.get('work_type_name'),
                'plot': work.get('plot'),
                'date': str(work.get('work_date')),
                'cost': float(work.get('total_cost') or 0),
                'anomaly_score': result.get('anomaly_score'),
                'message': result.get('message')
            })
    
    return {
        'total_checked': len(recent_works),
        'anomalies_found': len(anomalies),
        'anomalies': anomalies,
        'date_range': f"{DATA_START_DATE} to {DATA_END_DATE}"
    }
