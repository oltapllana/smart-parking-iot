#!/usr/bin/env python3
"""
Smart Parking ML Service - Parking Demand Prediction
Predicts parking availability and demands using ML models
"""

import numpy as np
import json
import pickle
import os
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import joblib


class ParkingMLService:
    def __init__(self, model_dir='models'):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        
        # Models
        self.availability_classifier = None
        self.demand_predictor = None
        self.occupancy_clusterer = None
        self.scaler = StandardScaler()
        
        # Training data history
        self.training_data = []
        self.occupancy_history = []
        
        self._initialize_models()
        
    def _initialize_models(self):
        """Initialize or load ML models"""
        # Load existing models if available
        availability_path = os.path.join(self.model_dir, 'availability_classifier.pkl')
        demand_path = os.path.join(self.model_dir, 'demand_predictor.pkl')
        clusterer_path = os.path.join(self.model_dir, 'occupancy_clusterer.pkl')
        
        if os.path.exists(availability_path):
            self.availability_classifier = joblib.load(availability_path)
        else:
            # Initialize with dummy classifier
            self.availability_classifier = RandomForestClassifier(n_estimators=10, random_state=42)
        
        if os.path.exists(demand_path):
            self.demand_predictor = joblib.load(demand_path)
        else:
            self.demand_predictor = RandomForestRegressor(n_estimators=10, random_state=42)
        
        if os.path.exists(clusterer_path):
            self.occupancy_clusterer = joblib.load(clusterer_path)
        else:
            self.occupancy_clusterer = KMeans(n_clusters=3, random_state=42)
    
    def extract_features(self, lot_data, historical_data=None):
        """Extract features from parking lot data"""
        features = []
        
        # Current occupancy rate
        features.append(lot_data.get('occupancy_rate', 0) / 100.0)
        
        # Hour of day (0-23)
        hour = datetime.now().hour
        features.append(hour / 24.0)
        
        # Day of week (0-6, 0=Monday)
        day_of_week = datetime.now().weekday()
        features.append(day_of_week / 7.0)
        
        # Zone statistics
        zone_stats = lot_data.get('zone_statistics', {})
        for zone in sorted(zone_stats.keys()):
            zone_occ = zone_stats[zone].get('occupancy_rate', 0) / 100.0
            features.append(zone_occ)
        
        # Historical trend (if available)
        if historical_data and len(historical_data) > 0:
            avg_occupancy = np.mean([d.get('occupancy_rate', 0) for d in historical_data[-10:]])
            features.append(avg_occupancy / 100.0)
        else:
            features.append(0.5)
        
        return np.array([features])
    
    def predict_availability(self, lot_data, confidence_score=True):
        """
        Predict parking availability
        Returns: 'HIGH', 'MEDIUM', 'LOW', 'FULL'
        """
        occupancy_rate = lot_data.get('occupancy_rate', 0)
        
        # Simple rule-based prediction (can be enhanced with ML)
        if occupancy_rate >= 95:
            availability = 'FULL'
            confidence = 0.95
        elif occupancy_rate >= 80:
            availability = 'LOW'
            confidence = 0.85
        elif occupancy_rate >= 50:
            availability = 'MEDIUM'
            confidence = 0.80
        else:
            availability = 'HIGH'
            confidence = 0.90
        
        return {
            'availability': availability,
            'confidence': confidence,
            'occupancy_rate': occupancy_rate,
            'recommendation': self._get_recommendation(availability),
            'timestamp': datetime.now().isoformat()
        }
    
    def predict_demand(self, lot_data, time_horizon_minutes=30):
        """
        Predict parking demand in the next N minutes
        Returns: predicted demand level and trend
        """
        occupancy_rate = lot_data.get('occupancy_rate', 0)
        hour = datetime.now().hour
        
        # Simulate demand prediction based on time and occupancy
        base_demand = self._get_base_demand(hour)
        trend = self._calculate_trend(occupancy_rate)
        
        predicted_occupancy = occupancy_rate + (trend * (time_horizon_minutes / 60))
        predicted_occupancy = max(0, min(100, predicted_occupancy))
        
        return {
            'time_horizon': time_horizon_minutes,
            'predicted_occupancy_rate': predicted_occupancy,
            'base_demand': base_demand,
            'trend': trend,
            'demand_level': self._occupancy_to_demand(predicted_occupancy),
            'timestamp': datetime.now().isoformat()
        }
    
    def detect_anomalies(self, lot_data, historical_data=None):
        """Detect anomalies in parking patterns"""
        occupancy_rate = lot_data.get('occupancy_rate', 0)
        
        if not historical_data or len(historical_data) < 5:
            return {'anomaly_detected': 0, 'reason': 'insufficient_data'}
        
        # Calculate average and std from historical data
        recent_occupancy = [d.get('occupancy_rate', 0) for d in historical_data[-20:]]
        avg_occupancy = np.mean(recent_occupancy)
        std_occupancy = np.std(recent_occupancy)
        
        # Detect anomaly if current occupancy deviates significantly
        z_score = abs((occupancy_rate - avg_occupancy) / (std_occupancy + 0.001))
        anomaly_detected = 1 if z_score > 2.5 else 0
        
        return {
            'anomaly_detected': anomaly_detected,
            'z_score': float(z_score),
            'current_occupancy': float(occupancy_rate),
            'average_occupancy': float(avg_occupancy),
            'severity': 'high' if z_score > 3 else 'medium' if z_score > 2.5 else 'low'
        }
    
    def recommend_alternative_zone(self, lot_data):
        """Recommend alternative parking zone if current is full"""
        zone_stats = lot_data.get('zone_statistics', {})
        zones = []
        
        for zone, stats in zone_stats.items():
            occ_rate = stats.get('occupancy_rate', 0)
            available = stats.get('available', 0)
            zones.append({
                'zone': zone,
                'occupancy_rate': occ_rate,
                'available_spots': available,
                'score': available / (occ_rate + 1)  # Higher score = better
            })
        
        # Sort by score (descending)
        zones.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'recommended_zone': zones[0]['zone'] if zones else None,
            'alternatives': zones[:3],
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_recommendation(self, availability):
        """Get recommendation based on availability"""
        recommendations = {
            'HIGH': 'Parking is readily available. No issues.',
            'MEDIUM': 'Moderate availability. Expect to find parking with some search.',
            'LOW': 'Limited availability. May take time to find parking.',
            'FULL': 'Parking lot is full. Consider alternative locations.'
        }
        return recommendations.get(availability, 'No recommendation available')
    
    def _get_base_demand(self, hour):
        """Get base demand based on hour of day"""
        # Peak hours: 8-10am, 12-1pm, 5-7pm
        peak_hours = [8, 9, 12, 17, 18]
        if hour in peak_hours:
            return 'HIGH'
        elif hour in [7, 10, 11, 13, 19, 20]:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _calculate_trend(self, current_occupancy):
        """Calculate occupancy trend"""
        hour = datetime.now().hour
        
        # Simulate trend based on time of day
        if hour < 10:  # Morning: occupancy increasing
            return 2.0
        elif hour < 14:  # Midday: relatively stable
            return 0.5
        elif hour < 18:  # Afternoon: increasing
            return 1.5
        else:  # Evening: mixed
            return -0.5
    
    def _occupancy_to_demand(self, occupancy_rate):
        """Convert occupancy rate to demand level"""
        if occupancy_rate >= 80:
            return 'CRITICAL'
        elif occupancy_rate >= 60:
            return 'HIGH'
        elif occupancy_rate >= 40:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def train_models(self, training_data):
        """Train ML models with historical data"""
        if len(training_data) < 10:
            print("⚠️ Not enough training data")
            return False
        
        try:
            # Prepare data
            X = np.array([d['features'] for d in training_data])
            y_availability = np.array([d['availability_label'] for d in training_data])
            y_demand = np.array([d['demand_label'] for d in training_data])
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train models
            self.availability_classifier.fit(X_scaled, y_availability)
            self.demand_predictor.fit(X_scaled, y_demand)
            self.occupancy_clusterer.fit(X_scaled)
            
            # Save models
            joblib.dump(self.availability_classifier, 
                       os.path.join(self.model_dir, 'availability_classifier.pkl'))
            joblib.dump(self.demand_predictor,
                       os.path.join(self.model_dir, 'demand_predictor.pkl'))
            joblib.dump(self.occupancy_clusterer,
                       os.path.join(self.model_dir, 'occupancy_clusterer.pkl'))
            
            print("✅ Models trained and saved successfully")
            return True
        except Exception as e:
            print(f"❌ Error training models: {str(e)}")
            return False
    
    def get_analytics(self, lot_data, historical_data=None):
        """Get comprehensive parking analytics"""
        return {
            'availability_prediction': self.predict_availability(lot_data),
            'demand_prediction': self.predict_demand(lot_data),
            'zone_recommendation': self.recommend_alternative_zone(lot_data),
            'anomaly_detection': self.detect_anomalies(lot_data, historical_data),
            'timestamp': datetime.now().isoformat()
        }


# Example usage
if __name__ == '__main__':
    ml_service = ParkingMLService()
    
    # Sample parking lot data
    sample_data = {
        'occupancy_rate': 65.5,
        'occupied_spots': 118,
        'total_spots': 180,
        'zone_statistics': {
            'Zone-1': {'occupancy_rate': 70, 'occupied': 30, 'available': 15},
            'Zone-2': {'occupancy_rate': 60, 'occupied': 27, 'available': 18},
            'Zone-3': {'occupancy_rate': 65, 'occupied': 30, 'available': 15},
            'Zone-4': {'occupancy_rate': 68, 'occupied': 31, 'available': 14}
        }
    }
    
    analytics = ml_service.get_analytics(sample_data)
    print(json.dumps(analytics, indent=2))
