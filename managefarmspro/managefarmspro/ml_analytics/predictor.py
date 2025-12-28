# Copyright (c) 2024-2025, FigAi GenAi Solutions and contributors
# ML Analytics Predictor for ManageFarmsPro
# Author: Khalandar Sihan (2303RES181)
# 
# Implements:
# - Random Forest Regressor for cost prediction
# - Gradient Boosting Regressor for resource forecasting
# - Isolation Forest for anomaly detection
# - Time Series analysis for budget forecasting

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months, now_datetime
from datetime import datetime, timedelta
import os
import pickle

# Try to import ML libraries
try:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, IsolationForest
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    np = None
    pd = None

# ============ DATE RANGE CONFIGURATION ============
# Set the date range for demo/project work data
DATA_START_DATE = '2025-01-01'
DATA_END_DATE = '2025-09-30'
# ==================================================


def add_months_to_date(source_date, months):
    """Add months to a date, handling year rollover correctly"""
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                                  31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return datetime(year, month, day)


class MLPredictor:
    """
    Machine Learning Predictor for ManageFarmsPro
    
    Models:
    1. Cost Predictor (Random Forest) - Predicts work order costs
    2. Resource Predictor (Gradient Boosting) - Forecasts labor, equipment, materials
    3. Anomaly Detector (Isolation Forest) - Detects unusual work orders
    """
    
    def __init__(self):
        self.cost_predictor = None
        self.resource_predictor = None
        self.anomaly_detector = None
        self.scaler = None
        self.label_encoders = {}
        self.model_path = self._get_model_path()
        self.feature_columns = [
            'work_type_encoded', 'plot_encoded', 'cluster_encoded',
            'plot_area', 'supervision_charge', 'monthly_budget',
            'month', 'quarter', 'day_of_week', 'year',
            'labor_count', 'equipment_count', 'material_count'
        ]
        
        # Try to load existing models
        self._load_models()
    
    def _get_model_path(self):
        """Get the path for storing ML models"""
        site_path = frappe.get_site_path()
        models_dir = os.path.join(site_path, 'private', 'ml_models')
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)
        return models_dir
    
    def _save_models(self):
        """Save trained models to disk"""
        try:
            if self.cost_predictor:
                with open(os.path.join(self.model_path, 'cost_predictor.pkl'), 'wb') as f:
                    pickle.dump(self.cost_predictor, f)
            
            if self.resource_predictor:
                with open(os.path.join(self.model_path, 'resource_predictor.pkl'), 'wb') as f:
                    pickle.dump(self.resource_predictor, f)
            
            if self.anomaly_detector:
                with open(os.path.join(self.model_path, 'anomaly_detector.pkl'), 'wb') as f:
                    pickle.dump(self.anomaly_detector, f)
            
            if self.scaler:
                with open(os.path.join(self.model_path, 'scaler.pkl'), 'wb') as f:
                    pickle.dump(self.scaler, f)
            
            if self.label_encoders:
                with open(os.path.join(self.model_path, 'label_encoders.pkl'), 'wb') as f:
                    pickle.dump(self.label_encoders, f)
                    
            return True
        except Exception as e:
            frappe.log_error(f"Error saving ML models: {str(e)}", "ML Model Save Error")
            return False
    
    def _load_models(self):
        """Load trained models from disk"""
        try:
            cost_path = os.path.join(self.model_path, 'cost_predictor.pkl')
            if os.path.exists(cost_path):
                with open(cost_path, 'rb') as f:
                    self.cost_predictor = pickle.load(f)
            
            resource_path = os.path.join(self.model_path, 'resource_predictor.pkl')
            if os.path.exists(resource_path):
                with open(resource_path, 'rb') as f:
                    self.resource_predictor = pickle.load(f)
            
            anomaly_path = os.path.join(self.model_path, 'anomaly_detector.pkl')
            if os.path.exists(anomaly_path):
                with open(anomaly_path, 'rb') as f:
                    self.anomaly_detector = pickle.load(f)
            
            scaler_path = os.path.join(self.model_path, 'scaler.pkl')
            if os.path.exists(scaler_path):
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
            
            encoders_path = os.path.join(self.model_path, 'label_encoders.pkl')
            if os.path.exists(encoders_path):
                with open(encoders_path, 'rb') as f:
                    self.label_encoders = pickle.load(f)
                    
        except Exception as e:
            frappe.log_error(f"Error loading ML models: {str(e)}", "ML Model Load Error")
    
    def get_training_data(self):
        """Fetch and prepare training data from Work doctype (Jan 2025 - Sep 2025)"""
        if not ML_AVAILABLE:
            return None
        
        # Get submitted works with all related data within date range
        works = frappe.db.sql("""
            SELECT 
                w.name,
                w.work_type_name,
                w.plot,
                w.work_date,
                w.total_cost,
                w.customer,
                p.area as plot_area,
                p.cluster,
                p.supervision_charge,
                p.monthly_maintenance_budget,
                (SELECT COUNT(*) FROM `tabLabor Child` lc WHERE lc.parent = w.name) as labor_count,
                (SELECT COUNT(*) FROM `tabEquipment Child` ec WHERE ec.parent = w.name) as equipment_count,
                (SELECT COUNT(*) FROM `tabMaterial Child` mc WHERE mc.parent = w.name) as material_count
            FROM `tabWork` w
            LEFT JOIN `tabPlot` p ON w.plot = p.name
            WHERE w.docstatus = 1
            AND w.total_cost > 0
            AND w.work_date BETWEEN %s AND %s
            ORDER BY w.work_date DESC
            LIMIT 5000
        """, (DATA_START_DATE, DATA_END_DATE), as_dict=True)
        
        if not works:
            return None
        
        # Convert frappe._dict to regular dict for pandas compatibility
        works_list = [dict(w) for w in works]
        df = pd.DataFrame(works_list)
        
        # Extract date features
        df['work_date'] = pd.to_datetime(df['work_date'])
        df['month'] = df['work_date'].dt.month
        df['quarter'] = df['work_date'].dt.quarter
        df['day_of_week'] = df['work_date'].dt.dayofweek + 1
        df['year'] = df['work_date'].dt.year
        
        # Fill missing values
        df['plot_area'] = df['plot_area'].fillna(0).astype(float)
        df['supervision_charge'] = df['supervision_charge'].fillna(0).astype(float)
        df['monthly_maintenance_budget'] = df['monthly_maintenance_budget'].fillna(0).astype(float)
        df['labor_count'] = df['labor_count'].fillna(0).astype(int)
        df['equipment_count'] = df['equipment_count'].fillna(0).astype(int)
        df['material_count'] = df['material_count'].fillna(0).astype(int)
        
        return df
    
    def _encode_features(self, df, fit=False):
        """Encode categorical features"""
        categorical_cols = ['work_type_name', 'plot', 'cluster']
        
        for col in categorical_cols:
            encoded_col = f'{col}_encoded' if col != 'work_type_name' else 'work_type_encoded'
            if col == 'plot':
                encoded_col = 'plot_encoded'
            elif col == 'cluster':
                encoded_col = 'cluster_encoded'
            else:
                encoded_col = 'work_type_encoded'
            
            if fit:
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                # Handle unknown categories
                df[col] = df[col].fillna('Unknown')
                self.label_encoders[col].fit(df[col].astype(str))
            
            if col in self.label_encoders:
                df[col] = df[col].fillna('Unknown')
                # Handle unseen categories
                known_classes = set(self.label_encoders[col].classes_)
                df[col] = df[col].apply(lambda x: x if x in known_classes else 'Unknown')
                if 'Unknown' not in self.label_encoders[col].classes_:
                    self.label_encoders[col].classes_ = np.append(self.label_encoders[col].classes_, 'Unknown')
                df[encoded_col] = self.label_encoders[col].transform(df[col].astype(str))
            else:
                df[encoded_col] = 0
        
        return df
    
    def train_models(self):
        """Train all ML models"""
        if not ML_AVAILABLE:
            return {
                'success': False,
                'message': 'ML libraries not available. Please install scikit-learn, pandas, and numpy.'
            }
        
        df = self.get_training_data()
        
        if df is None or len(df) < 10:
            return {
                'success': False,
                'message': f'Insufficient training data. Need at least 10 submitted works in date range ({DATA_START_DATE} to {DATA_END_DATE}), found {len(df) if df is not None else 0}.'
            }
        
        try:
            # Encode categorical features
            df = self._encode_features(df, fit=True)
            
            # Rename for consistency
            df['monthly_budget'] = df['monthly_maintenance_budget']
            
            # Prepare features
            feature_cols = [
                'work_type_encoded', 'plot_encoded', 'cluster_encoded',
                'plot_area', 'supervision_charge', 'monthly_budget',
                'month', 'quarter', 'day_of_week', 'year',
                'labor_count', 'equipment_count', 'material_count'
            ]
            
            # Ensure all feature columns exist
            for col in feature_cols:
                if col not in df.columns:
                    df[col] = 0
            
            X = df[feature_cols].values
            y_cost = df['total_cost'].values
            
            # Scale features
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y_cost, test_size=0.2, random_state=42
            )
            
            # Train Cost Predictor (Random Forest)
            self.cost_predictor = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            self.cost_predictor.fit(X_train, y_train)
            
            # Evaluate
            y_pred = self.cost_predictor.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)
            
            # Train Resource Predictor (Gradient Boosting)
            # Predict total resources as a proxy
            y_resources = df['labor_count'] + df['equipment_count'] + df['material_count']
            X_resource = df[['work_type_encoded', 'plot_encoded', 'plot_area', 
                            'monthly_budget', 'month', 'total_cost']].values
            
            if len(X_resource) > 10:
                self.resource_predictor = GradientBoostingRegressor(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=5,
                    random_state=42
                )
                scaler_resource = StandardScaler()
                X_resource_scaled = scaler_resource.fit_transform(X_resource)
                self.resource_predictor.fit(X_resource_scaled, y_resources)
            
            # Train Anomaly Detector (Isolation Forest)
            self.anomaly_detector = IsolationForest(
                contamination=0.1,
                random_state=42,
                n_jobs=-1
            )
            self.anomaly_detector.fit(X_scaled)
            
            # Save models
            self._save_models()
            
            return {
                'success': True,
                'message': 'Models trained successfully',
                'metrics': {
                    'mae': round(mae, 2),
                    'rmse': round(rmse, 2),
                    'r2_score': round(r2, 4),
                    'training_samples': len(df),
                    'test_samples': len(X_test),
                    'date_range': f"{DATA_START_DATE} to {DATA_END_DATE}"
                }
            }
            
        except Exception as e:
            frappe.log_error(f"Error training models: {str(e)}\n{frappe.get_traceback()}", "ML Training Error")
            return {
                'success': False,
                'message': f'Error training models: {str(e)}'
            }
    
    def predict_cost(self, work_data):
        """
        Predict cost for a work order
        
        Args:
            work_data: dict with keys: work_type_name, plot, labor_count, equipment_count, material_count
        
        Returns:
            Predicted cost (float)
        """
        if not ML_AVAILABLE:
            return self._fallback_prediction(work_data)
        
        if self.cost_predictor is None:
            return self._fallback_prediction(work_data)
        
        try:
            # Get plot details
            plot_data = frappe.db.get_value(
                "Plot", 
                work_data.get('plot'),
                ['area', 'cluster', 'supervision_charge', 'monthly_maintenance_budget'],
                as_dict=True
            ) or {}
            
            # Prepare features - use a date in the middle of our range
            # Use September 2025 as "current"
            features = {
                'work_type_name': work_data.get('work_type_name', 'Unknown'),
                'plot': work_data.get('plot', 'Unknown'),
                'cluster': plot_data.get('cluster', 'Unknown'),
                'plot_area': flt(plot_data.get('area', 0)),
                'supervision_charge': flt(plot_data.get('supervision_charge', 0)),
                'monthly_budget': flt(plot_data.get('monthly_maintenance_budget', 0)),
                'month': 9,  # September
                'quarter': 3,
                'day_of_week': 3,  # Wednesday
                'year': 2025,
                'labor_count': work_data.get('labor_count', 1),
                'equipment_count': work_data.get('equipment_count', 1),
                'material_count': work_data.get('material_count', 1)
            }
            
            # Create DataFrame - single row
            df = pd.DataFrame([features])
            
            # Encode features
            df = self._encode_features(df, fit=False)
            df['monthly_budget'] = df['monthly_budget'] if 'monthly_budget' in df.columns else 0
            
            # Prepare feature vector
            feature_cols = [
                'work_type_encoded', 'plot_encoded', 'cluster_encoded',
                'plot_area', 'supervision_charge', 'monthly_budget',
                'month', 'quarter', 'day_of_week', 'year',
                'labor_count', 'equipment_count', 'material_count'
            ]
            
            for col in feature_cols:
                if col not in df.columns:
                    df[col] = 0
            
            X = df[feature_cols].values
            
            # Scale
            if self.scaler:
                X_scaled = self.scaler.transform(X)
            else:
                X_scaled = X
            
            # Predict
            prediction = self.cost_predictor.predict(X_scaled)[0]
            
            return max(0, prediction)  # Ensure non-negative
            
        except Exception as e:
            frappe.log_error(f"Prediction error: {str(e)}", "ML Prediction Error")
            return self._fallback_prediction(work_data)
    
    def _fallback_prediction(self, work_data):
        """Fallback prediction using historical averages from date range"""
        avg_cost = frappe.db.sql("""
            SELECT AVG(total_cost) as avg_cost
            FROM `tabWork`
            WHERE docstatus = 1
            AND work_type_name = %s
            AND total_cost > 0
            AND work_date BETWEEN %s AND %s
        """, (work_data.get('work_type_name'), DATA_START_DATE, DATA_END_DATE), as_dict=True)
        
        if avg_cost and avg_cost[0].get('avg_cost'):
            return float(avg_cost[0]['avg_cost'])
        
        # Global average
        global_avg = frappe.db.sql("""
            SELECT AVG(total_cost) as avg_cost
            FROM `tabWork`
            WHERE docstatus = 1
            AND total_cost > 0
            AND work_date BETWEEN %s AND %s
        """, (DATA_START_DATE, DATA_END_DATE), as_dict=True)
        
        if global_avg and global_avg[0].get('avg_cost'):
            return float(global_avg[0]['avg_cost'])
        
        return 0
    
    def predict_resources(self, work_data):
        """
        Predict required resources for a work order
        
        Returns:
            dict with predicted_labor, predicted_equipment, predicted_material
        """
        # Get historical averages for this work type from date range
        avg_resources = frappe.db.sql("""
            SELECT 
                AVG((SELECT COUNT(*) FROM `tabLabor Child` lc WHERE lc.parent = w.name)) as avg_labor,
                AVG((SELECT COUNT(*) FROM `tabEquipment Child` ec WHERE ec.parent = w.name)) as avg_equipment,
                AVG((SELECT COUNT(*) FROM `tabMaterial Child` mc WHERE mc.parent = w.name)) as avg_material
            FROM `tabWork` w
            WHERE w.docstatus = 1
            AND w.work_type_name = %s
            AND w.work_date BETWEEN %s AND %s
        """, (work_data.get('work_type_name'), DATA_START_DATE, DATA_END_DATE), as_dict=True)
        
        if avg_resources and avg_resources[0]:
            return {
                'predicted_labor': max(1, round(flt(avg_resources[0].get('avg_labor', 1)))),
                'predicted_equipment': max(1, round(flt(avg_resources[0].get('avg_equipment', 1)))),
                'predicted_material': max(1, round(flt(avg_resources[0].get('avg_material', 1)))),
                'confidence': 'high' if avg_resources[0].get('avg_labor') else 'low'
            }
        
        return {
            'predicted_labor': 1,
            'predicted_equipment': 1,
            'predicted_material': 1,
            'confidence': 'low'
        }
    
    def detect_anomaly(self, work_data):
        """
        Detect if a work order is anomalous
        
        Returns:
            dict with is_anomaly, anomaly_score, message
        """
        if not ML_AVAILABLE or self.anomaly_detector is None:
            return self._fallback_anomaly_detection(work_data)
        
        try:
            # Get plot details
            plot_data = frappe.db.get_value(
                "Plot", 
                work_data.get('plot'),
                ['area', 'cluster', 'supervision_charge', 'monthly_maintenance_budget'],
                as_dict=True
            ) or {}
            
            # Prepare features
            work_date = work_data.get('work_date') or datetime(2025, 9, 15)
            if isinstance(work_date, str):
                work_date = datetime.strptime(work_date, '%Y-%m-%d')
            
            features = {
                'work_type_name': work_data.get('work_type_name', 'Unknown'),
                'plot': work_data.get('plot', 'Unknown'),
                'cluster': plot_data.get('cluster', 'Unknown'),
                'plot_area': flt(plot_data.get('area', 0)),
                'supervision_charge': flt(plot_data.get('supervision_charge', 0)),
                'monthly_budget': flt(plot_data.get('monthly_maintenance_budget', 0)),
                'month': work_date.month,
                'quarter': (work_date.month - 1) // 3 + 1,
                'day_of_week': work_date.weekday() + 1,
                'year': work_date.year,
                'labor_count': work_data.get('labor_count', 0),
                'equipment_count': work_data.get('equipment_count', 0),
                'material_count': work_data.get('material_count', 0)
            }
            
            df = pd.DataFrame([features])
            df = self._encode_features(df, fit=False)
            
            feature_cols = [
                'work_type_encoded', 'plot_encoded', 'cluster_encoded',
                'plot_area', 'supervision_charge', 'monthly_budget',
                'month', 'quarter', 'day_of_week', 'year',
                'labor_count', 'equipment_count', 'material_count'
            ]
            
            for col in feature_cols:
                if col not in df.columns:
                    df[col] = 0
            
            X = df[feature_cols].values
            
            if self.scaler:
                X_scaled = self.scaler.transform(X)
            else:
                X_scaled = X
            
            # Predict anomaly (-1 for anomaly, 1 for normal)
            prediction = self.anomaly_detector.predict(X_scaled)[0]
            score = self.anomaly_detector.score_samples(X_scaled)[0]
            
            is_anomaly = prediction == -1
            
            return {
                'is_anomaly': is_anomaly,
                'anomaly_score': float(score),
                'status': 'anomaly' if is_anomaly else 'normal',
                'message': 'This work order has unusual characteristics' if is_anomaly else 'Work order appears normal'
            }
            
        except Exception as e:
            frappe.log_error(f"Anomaly detection error: {str(e)}", "ML Anomaly Error")
            return self._fallback_anomaly_detection(work_data)
    
    def _fallback_anomaly_detection(self, work_data):
        """Fallback anomaly detection using statistical methods"""
        total_cost = flt(work_data.get('total_cost', 0))
        work_type = work_data.get('work_type_name')
        
        if not total_cost or not work_type:
            return {
                'is_anomaly': False,
                'anomaly_score': 0,
                'status': 'unknown',
                'message': 'Insufficient data for anomaly detection'
            }
        
        # Get statistics for this work type from date range
        stats = frappe.db.sql("""
            SELECT 
                AVG(total_cost) as mean_cost,
                STDDEV(total_cost) as std_cost
            FROM `tabWork`
            WHERE docstatus = 1
            AND work_type_name = %s
            AND total_cost > 0
            AND work_date BETWEEN %s AND %s
        """, (work_type, DATA_START_DATE, DATA_END_DATE), as_dict=True)
        
        if stats and stats[0].get('mean_cost') and stats[0].get('std_cost'):
            mean_cost = float(stats[0]['mean_cost'])
            std_cost = float(stats[0]['std_cost'])
            
            if std_cost > 0:
                z_score = abs(total_cost - mean_cost) / std_cost
                is_anomaly = z_score > 2.5  # More than 2.5 standard deviations
                
                return {
                    'is_anomaly': is_anomaly,
                    'anomaly_score': float(z_score),
                    'status': 'anomaly' if is_anomaly else 'normal',
                    'message': f'Cost is {z_score:.1f} standard deviations from mean' if is_anomaly else 'Cost is within normal range'
                }
        
        return {
            'is_anomaly': False,
            'anomaly_score': 0,
            'status': 'normal',
            'message': 'Work order appears normal (insufficient historical data for detailed analysis)'
        }
    
    def forecast_budget(self, plot_name, months_ahead=3):
        """
        Forecast budget usage for a plot
        
        Args:
            plot_name: Name of the plot
            months_ahead: Number of months to forecast
        
        Returns:
            List of monthly forecasts with confidence intervals
        """
        if not ML_AVAILABLE:
            return self._fallback_budget_forecast(plot_name, months_ahead)
        
        try:
            # Get historical spending for this plot within date range
            historical_data = frappe.db.sql("""
                SELECT 
                    DATE_FORMAT(work_date, '%%Y-%%m') as month,
                    SUM(total_cost) as monthly_cost,
                    COUNT(*) as work_count
                FROM `tabWork`
                WHERE docstatus = 1
                AND plot = %s
                AND work_date BETWEEN %s AND %s
                GROUP BY DATE_FORMAT(work_date, '%%Y-%%m')
                ORDER BY month
            """, (plot_name, DATA_START_DATE, DATA_END_DATE), as_dict=True)
            
            if not historical_data or len(historical_data) < 3:
                return self._fallback_budget_forecast(plot_name, months_ahead)
            
            # Convert to regular dict for pandas
            historical_list = [dict(d) for d in historical_data]
            df = pd.DataFrame(historical_list)
            df['monthly_cost'] = df['monthly_cost'].astype(float)
            
            # Simple weighted moving average forecast
            weights = np.array([0.1, 0.2, 0.3, 0.4])[-len(df):]
            weights = weights / weights.sum()
            
            recent_costs = df['monthly_cost'].tail(len(weights)).values
            base_forecast = np.average(recent_costs, weights=weights)
            
            # Calculate seasonality factor
            df['month_num'] = pd.to_datetime(df['month']).dt.month
            monthly_avg = df.groupby('month_num')['monthly_cost'].mean()
            overall_avg = df['monthly_cost'].mean()
            
            forecasts = []
            # Start forecasting from October 2025
            forecast_start = datetime(2025, 10, 1)
            
            for i in range(months_ahead):
                # Use proper month addition instead of timedelta
                forecast_date = add_months_to_date(forecast_start, i)
                forecast_month = forecast_date.month
                
                # Apply seasonality
                if forecast_month in monthly_avg.index and overall_avg > 0:
                    seasonality = monthly_avg[forecast_month] / overall_avg
                else:
                    seasonality = 1.0
                
                predicted = base_forecast * seasonality
                
                # Confidence interval (simple approach)
                std_dev = df['monthly_cost'].std()
                confidence_lower = max(0, predicted - 1.96 * std_dev)
                confidence_upper = predicted + 1.96 * std_dev
                
                forecasts.append({
                    'month': forecast_date.strftime('%Y-%m'),
                    'month_name': forecast_date.strftime('%B %Y'),
                    'predicted_cost': round(predicted, 2),
                    'confidence_lower': round(confidence_lower, 2),
                    'confidence_upper': round(confidence_upper, 2),
                    'seasonality_factor': round(seasonality, 2)
                })
            
            return {
                'success': True,
                'plot': plot_name,
                'forecasts': forecasts,
                'historical_average': round(overall_avg, 2),
                'data_points': len(df),
                'date_range': f"{DATA_START_DATE} to {DATA_END_DATE}"
            }
            
        except Exception as e:
            frappe.log_error(f"Budget forecast error: {str(e)}", "ML Forecast Error")
            return self._fallback_budget_forecast(plot_name, months_ahead)
    
    def _fallback_budget_forecast(self, plot_name, months_ahead):
        """Fallback budget forecast using simple averages from date range"""
        avg_data = frappe.db.sql("""
            SELECT 
                AVG(total_cost) as avg_monthly,
                COUNT(*) as total_works
            FROM `tabWork`
            WHERE docstatus = 1
            AND plot = %s
            AND work_date BETWEEN %s AND %s
        """, (plot_name, DATA_START_DATE, DATA_END_DATE), as_dict=True)
        
        avg_monthly = float(avg_data[0].get('avg_monthly') or 0) if avg_data else 0
        
        forecasts = []
        # Start forecasting from October 2025
        forecast_start = datetime(2025, 10, 1)
        
        for i in range(months_ahead):
            # Use proper month addition instead of timedelta
            forecast_date = add_months_to_date(forecast_start, i)
            forecasts.append({
                'month': forecast_date.strftime('%Y-%m'),
                'month_name': forecast_date.strftime('%B %Y'),
                'predicted_cost': round(avg_monthly, 2),
                'confidence_lower': round(avg_monthly * 0.7, 2),
                'confidence_upper': round(avg_monthly * 1.3, 2),
                'seasonality_factor': 1.0
            })
        
        return {
            'success': True,
            'plot': plot_name,
            'forecasts': forecasts,
            'historical_average': round(avg_monthly, 2),
            'data_points': avg_data[0].get('total_works', 0) if avg_data else 0,
            'note': 'Using simple average (insufficient data for advanced forecasting)',
            'date_range': f"{DATA_START_DATE} to {DATA_END_DATE}"
        }


# Singleton instance
_predictor = None

def get_predictor():
    """Get or create singleton predictor instance"""
    global _predictor
    if _predictor is None:
        _predictor = MLPredictor()
    return _predictor


# ==================== API ENDPOINTS ====================

@frappe.whitelist()
def train_models():
    """API endpoint to train ML models"""
    predictor = get_predictor()
    return predictor.train_models()


@frappe.whitelist()
def predict_work_cost(work_type_name, plot, labor_count=1, equipment_count=1, material_count=1):
    """API endpoint to predict work cost"""
    predictor = get_predictor()
    
    work_data = {
        'work_type_name': work_type_name,
        'plot': plot,
        'labor_count': int(labor_count),
        'equipment_count': int(equipment_count),
        'material_count': int(material_count)
    }
    
    predicted_cost = predictor.predict_cost(work_data)
    predicted_resources = predictor.predict_resources(work_data)
    
    return {
        'predicted_cost': round(predicted_cost, 2),
        'resources': predicted_resources,
        'fallback': predictor.cost_predictor is None
    }


@frappe.whitelist()
def check_anomaly(work_name):
    """API endpoint to check if a work order is anomalous"""
    predictor = get_predictor()
    
    # Get work data
    work = frappe.get_doc("Work", work_name)
    
    # Count child items
    labor_count = len(work.labor_table) if work.labor_table else 0
    equipment_count = len(work.equipment_table) if work.equipment_table else 0
    material_count = len(work.material_table) if work.material_table else 0
    
    work_data = {
        'work_type_name': work.work_type_name,
        'plot': work.plot,
        'work_date': work.work_date,
        'total_cost': work.total_cost,
        'labor_count': labor_count,
        'equipment_count': equipment_count,
        'material_count': material_count
    }
    
    return predictor.detect_anomaly(work_data)


@frappe.whitelist()
def forecast_budget(plot_name, months_ahead=3):
    """API endpoint to forecast budget for a plot"""
    predictor = get_predictor()
    return predictor.forecast_budget(plot_name, int(months_ahead))


@frappe.whitelist()
def get_prediction_insights(plot_name=None):
    """Get ML prediction insights and model status"""
    predictor = get_predictor()
    
    insights = {
        'ml_available': ML_AVAILABLE,
        'models_trained': {
            'cost_predictor': predictor.cost_predictor is not None,
            'resource_predictor': predictor.resource_predictor is not None,
            'anomaly_detector': predictor.anomaly_detector is not None
        },
        'total_training_data': frappe.db.count("Work", filters={
            "docstatus": 1,
            "work_date": ["between", [DATA_START_DATE, DATA_END_DATE]]
        }),
        'date_range': f"{DATA_START_DATE} to {DATA_END_DATE}"
    }
    
    if plot_name:
        insights['plot_stats'] = frappe.db.sql("""
            SELECT 
                COUNT(*) as total_works,
                SUM(total_cost) as total_spent,
                AVG(total_cost) as avg_cost
            FROM `tabWork`
            WHERE docstatus = 1 
            AND plot = %s
            AND work_date BETWEEN %s AND %s
        """, (plot_name, DATA_START_DATE, DATA_END_DATE), as_dict=True)[0]
    
    return insights