#!/usr/bin/env python3
"""
Smart Parking ML Service - Parking Demand Prediction

AI/ML component of the IoT system. Trains real scikit-learn models
(RandomForest classifier + regressor) on synthetic, time-of-day driven
parking data and uses them for live predictions. Falls back to rule-based
logic only if the trained model is unavailable.
"""

import numpy as np
import json
import os
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error
import joblib


# Availability class labels (output of the classifier)
AVAILABILITY_CLASSES = ['HIGH', 'MEDIUM', 'LOW', 'FULL']


class ParkingMLService:
    def __init__(self, model_dir='models', auto_train=True):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)

        # Models
        self.availability_classifier = None
        self.demand_predictor = None
        self.occupancy_clusterer = None
        self.scaler = StandardScaler()

        # Metadata about the trained models (exposed via the API)
        self.model_info = {
            'trained': False,
            'algorithm': 'RandomForest',
            'classifier_accuracy': None,
            'regressor_mae': None,
            'training_samples': 0,
            'features': ['occupancy_rate', 'hour_of_day', 'day_of_week',
                         'is_weekend', 'recent_trend'],
            'trained_at': None
        }

        # Training data history
        self.training_data = []
        self.occupancy_history = []

        self._initialize_models(auto_train)

    # ------------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------------
    def _initialize_models(self, auto_train=True):
        """Load existing models from disk, otherwise train fresh ones."""
        availability_path = os.path.join(self.model_dir, 'availability_classifier.pkl')
        demand_path = os.path.join(self.model_dir, 'demand_predictor.pkl')
        clusterer_path = os.path.join(self.model_dir, 'occupancy_clusterer.pkl')
        scaler_path = os.path.join(self.model_dir, 'scaler.pkl')
        info_path = os.path.join(self.model_dir, 'model_info.json')

        models_exist = (os.path.exists(availability_path) and
                        os.path.exists(demand_path) and
                        os.path.exists(scaler_path))

        if models_exist:
            try:
                self.availability_classifier = joblib.load(availability_path)
                self.demand_predictor = joblib.load(demand_path)
                self.scaler = joblib.load(scaler_path)
                if os.path.exists(clusterer_path):
                    self.occupancy_clusterer = joblib.load(clusterer_path)
                if os.path.exists(info_path):
                    with open(info_path) as f:
                        self.model_info = json.load(f)
                print("✅ ML models loaded from disk")
                return
            except Exception as e:
                print(f"⚠️ Could not load saved models ({e}); retraining...")

        # No usable models on disk
        self.availability_classifier = RandomForestClassifier(
            n_estimators=80, max_depth=10, random_state=42)
        self.demand_predictor = RandomForestRegressor(
            n_estimators=80, max_depth=10, random_state=42)
        self.occupancy_clusterer = KMeans(n_clusters=3, n_init=10, random_state=42)

        if auto_train:
            self.train_on_synthetic_data()

    # ------------------------------------------------------------------
    # Feature engineering (fixed-length vector so the model is stable)
    # ------------------------------------------------------------------
    def _feature_vector(self, occupancy_rate, hour, day_of_week, recent_trend=0.0):
        is_weekend = 1.0 if day_of_week >= 5 else 0.0
        return [
            occupancy_rate / 100.0,
            hour / 23.0,
            day_of_week / 6.0,
            is_weekend,
            recent_trend / 100.0,
        ]

    def extract_features(self, lot_data, historical_data=None):
        """Build the live feature vector from current lot data."""
        now = datetime.now()
        occupancy_rate = lot_data.get('occupancy_rate', 0)

        recent_trend = 0.0
        if historical_data and len(historical_data) >= 2:
            rates = [d.get('occupancy_rate', 0) for d in historical_data[-6:]]
            recent_trend = rates[-1] - rates[0]

        return np.array([self._feature_vector(
            occupancy_rate, now.hour, now.weekday(), recent_trend)])

    # ------------------------------------------------------------------
    # Synthetic training data
    # ------------------------------------------------------------------
    @staticmethod
    def _baseline_occupancy(hour, day_of_week):
        """Realistic average occupancy for a given hour/day (0-100)."""
        # Weekday commuter pattern with morning + evening peaks
        weekday_curve = {
            0: 8, 1: 5, 2: 4, 3: 4, 4: 6, 5: 15, 6: 35, 7: 60,
            8: 85, 9: 90, 10: 75, 11: 70, 12: 80, 13: 78, 14: 70,
            15: 68, 16: 75, 17: 92, 18: 88, 19: 65, 20: 45, 21: 30,
            22: 20, 23: 12
        }
        base = weekday_curve.get(hour, 40)
        if day_of_week >= 5:  # weekends are flatter and lower
            base = base * 0.6 + 10
        return base

    def _generate_synthetic_dataset(self, n_samples=4000):
        rng = np.random.default_rng(42)
        X, y_class, y_reg = [], [], []

        for _ in range(n_samples):
            hour = int(rng.integers(0, 24))
            day = int(rng.integers(0, 7))
            base = self._baseline_occupancy(hour, day)
            noise = rng.normal(0, 8)
            occ = float(np.clip(base + noise, 0, 100))

            # Recent trend correlated with the slope of the daily curve
            next_base = self._baseline_occupancy((hour + 1) % 24, day)
            trend = (next_base - base) + rng.normal(0, 5)

            X.append(self._feature_vector(occ, hour, day, trend))

            # Regression target: occupancy ~30 min ahead (genuinely predictive)
            future = float(np.clip(base + 0.5 * trend + rng.normal(0, 6), 0, 100))
            y_reg.append(future)

            # Classifier predicts the FUTURE availability class from the
            # current state — a real predictive task, not a trivial threshold.
            if future >= 95:
                y_class.append('FULL')
            elif future >= 80:
                y_class.append('LOW')
            elif future >= 50:
                y_class.append('MEDIUM')
            else:
                y_class.append('HIGH')

        return np.array(X), np.array(y_class), np.array(y_reg)

    def train_on_synthetic_data(self, n_samples=4000):
        """Train and persist real ML models on synthetic IoT data."""
        print("🤖 Training ML models on synthetic parking data...")
        X, y_class, y_reg = self._generate_synthetic_dataset(n_samples)

        X_scaled = self.scaler.fit_transform(X)

        Xc_tr, Xc_te, yc_tr, yc_te = train_test_split(
            X_scaled, y_class, test_size=0.2, random_state=42)
        Xr_tr, Xr_te, yr_tr, yr_te = train_test_split(
            X_scaled, y_reg, test_size=0.2, random_state=42)

        self.availability_classifier.fit(Xc_tr, yc_tr)
        self.demand_predictor.fit(Xr_tr, yr_tr)
        self.occupancy_clusterer.fit(X_scaled)

        acc = accuracy_score(yc_te, self.availability_classifier.predict(Xc_te))
        mae = mean_absolute_error(yr_te, self.demand_predictor.predict(Xr_te))

        self.model_info.update({
            'trained': True,
            'algorithm': 'RandomForest',
            'classifier_accuracy': round(float(acc), 4),
            'regressor_mae': round(float(mae), 4),
            'training_samples': int(n_samples),
            'trained_at': datetime.now().isoformat()
        })

        self._save_models()
        print(f"✅ Models trained — availability accuracy={acc:.2%}, "
              f"demand MAE={mae:.2f}%")
        return self.model_info

    def _save_models(self):
        joblib.dump(self.availability_classifier,
                    os.path.join(self.model_dir, 'availability_classifier.pkl'))
        joblib.dump(self.demand_predictor,
                    os.path.join(self.model_dir, 'demand_predictor.pkl'))
        joblib.dump(self.occupancy_clusterer,
                    os.path.join(self.model_dir, 'occupancy_clusterer.pkl'))
        joblib.dump(self.scaler, os.path.join(self.model_dir, 'scaler.pkl'))
        with open(os.path.join(self.model_dir, 'model_info.json'), 'w') as f:
            json.dump(self.model_info, f, indent=2)

    def get_model_info(self):
        """Expose model metadata (feature importances + metrics)."""
        info = dict(self.model_info)
        try:
            if self.model_info.get('trained'):
                importances = self.availability_classifier.feature_importances_
                info['feature_importances'] = {
                    feat: round(float(imp), 4)
                    for feat, imp in zip(self.model_info['features'], importances)
                }
        except Exception:
            pass
        return info

    # ------------------------------------------------------------------
    # Predictions (ML first, rule-based fallback)
    # ------------------------------------------------------------------
    def predict_availability(self, lot_data, historical_data=None):
        """Predict availability class using the trained classifier."""
        occupancy_rate = lot_data.get('occupancy_rate', 0)

        if self.model_info.get('trained'):
            try:
                feats = self.scaler.transform(
                    self.extract_features(lot_data, historical_data))
                pred = self.availability_classifier.predict(feats)[0]
                proba = self.availability_classifier.predict_proba(feats)[0]
                confidence = float(np.max(proba))
                return {
                    'availability': str(pred),
                    'confidence': round(confidence, 3),
                    'occupancy_rate': occupancy_rate,
                    'recommendation': self._get_recommendation(str(pred)),
                    'model': 'RandomForestClassifier',
                    'class_probabilities': {
                        cls: round(float(p), 3)
                        for cls, p in zip(self.availability_classifier.classes_, proba)
                    },
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                print(f"⚠️ ML availability prediction failed, using rules: {e}")

        return self._rule_based_availability(occupancy_rate)

    def _rule_based_availability(self, occupancy_rate):
        if occupancy_rate >= 95:
            availability, confidence = 'FULL', 0.95
        elif occupancy_rate >= 80:
            availability, confidence = 'LOW', 0.85
        elif occupancy_rate >= 50:
            availability, confidence = 'MEDIUM', 0.80
        else:
            availability, confidence = 'HIGH', 0.90
        return {
            'availability': availability,
            'confidence': confidence,
            'occupancy_rate': occupancy_rate,
            'recommendation': self._get_recommendation(availability),
            'model': 'rule-based-fallback',
            'timestamp': datetime.now().isoformat()
        }

    def predict_demand(self, lot_data, time_horizon_minutes=30, historical_data=None):
        """Predict future occupancy using the trained regressor."""
        occupancy_rate = lot_data.get('occupancy_rate', 0)
        hour = datetime.now().hour

        if self.model_info.get('trained'):
            try:
                feats = self.scaler.transform(
                    self.extract_features(lot_data, historical_data))
                predicted = float(self.demand_predictor.predict(feats)[0])
                predicted = max(0, min(100, predicted))
                trend = predicted - occupancy_rate
                return {
                    'time_horizon': time_horizon_minutes,
                    'predicted_occupancy_rate': round(predicted, 1),
                    'current_occupancy_rate': round(occupancy_rate, 1),
                    'base_demand': self._get_base_demand(hour),
                    'trend': round(trend, 2),
                    'trend_direction': ('increasing' if trend > 2 else
                                        'decreasing' if trend < -2 else 'stable'),
                    'demand_level': self._occupancy_to_demand(predicted),
                    'model': 'RandomForestRegressor',
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                print(f"⚠️ ML demand prediction failed, using rules: {e}")

        # Rule-based fallback
        base_demand = self._get_base_demand(hour)
        trend = self._calculate_trend(occupancy_rate)
        predicted = max(0, min(100, occupancy_rate + (trend * (time_horizon_minutes / 60))))
        return {
            'time_horizon': time_horizon_minutes,
            'predicted_occupancy_rate': round(predicted, 1),
            'current_occupancy_rate': round(occupancy_rate, 1),
            'base_demand': base_demand,
            'trend': trend,
            'demand_level': self._occupancy_to_demand(predicted),
            'model': 'rule-based-fallback',
            'timestamp': datetime.now().isoformat()
        }

    def detect_anomalies(self, lot_data, historical_data=None):
        """Detect anomalies in parking patterns using Z-score analysis."""
        occupancy_rate = lot_data.get('occupancy_rate', 0)

        if not historical_data or len(historical_data) < 5:
            return {'anomaly_detected': 0, 'reason': 'insufficient_data'}

        recent_occupancy = [d.get('occupancy_rate', 0) for d in historical_data[-20:]]
        avg_occupancy = np.mean(recent_occupancy)
        std_occupancy = np.std(recent_occupancy)

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
        """Recommend alternative parking zone if current is full."""
        zone_stats = lot_data.get('zone_statistics', {})
        zones = []

        for zone, stats in zone_stats.items():
            occ_rate = stats.get('occupancy_rate', 0)
            available = stats.get('available', 0)
            zones.append({
                'zone': zone,
                'occupancy_rate': occ_rate,
                'available_spots': available,
                'score': available / (occ_rate + 1)
            })

        zones.sort(key=lambda x: x['score'], reverse=True)

        return {
            'recommended_zone': zones[0]['zone'] if zones else None,
            'alternatives': zones[:3],
            'timestamp': datetime.now().isoformat()
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_recommendation(self, availability):
        recommendations = {
            'HIGH': 'Parking is readily available. No issues.',
            'MEDIUM': 'Moderate availability. Expect to find parking with some search.',
            'LOW': 'Limited availability. May take time to find parking.',
            'FULL': 'Parking lot is full. Consider alternative locations.'
        }
        return recommendations.get(availability, 'No recommendation available')

    def _get_base_demand(self, hour):
        peak_hours = [8, 9, 12, 17, 18]
        if hour in peak_hours:
            return 'HIGH'
        elif hour in [7, 10, 11, 13, 19, 20]:
            return 'MEDIUM'
        else:
            return 'LOW'

    def _calculate_trend(self, current_occupancy):
        hour = datetime.now().hour
        if hour < 10:
            return 2.0
        elif hour < 14:
            return 0.5
        elif hour < 18:
            return 1.5
        else:
            return -0.5

    def _occupancy_to_demand(self, occupancy_rate):
        if occupancy_rate >= 80:
            return 'CRITICAL'
        elif occupancy_rate >= 60:
            return 'HIGH'
        elif occupancy_rate >= 40:
            return 'MEDIUM'
        else:
            return 'LOW'

    def get_analytics(self, lot_data, historical_data=None):
        """Get comprehensive parking analytics."""
        return {
            'availability_prediction': self.predict_availability(lot_data, historical_data),
            'demand_prediction': self.predict_demand(lot_data, historical_data=historical_data),
            'zone_recommendation': self.recommend_alternative_zone(lot_data),
            'anomaly_detection': self.detect_anomalies(lot_data, historical_data),
            'model_info': {
                'trained': self.model_info.get('trained'),
                'algorithm': self.model_info.get('algorithm'),
                'classifier_accuracy': self.model_info.get('classifier_accuracy')
            },
            'timestamp': datetime.now().isoformat()
        }


# Example usage
if __name__ == '__main__':
    ml_service = ParkingMLService()

    print("\n=== Model Info ===")
    print(json.dumps(ml_service.get_model_info(), indent=2))

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

    print("\n=== Analytics ===")
    print(json.dumps(ml_service.get_analytics(sample_data), indent=2))
