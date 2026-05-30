#!/usr/bin/env python3
"""
Smart Parking Alert Engine
Monitors parking lot conditions and generates alerts
"""

from datetime import datetime, timedelta
from enum import Enum
import json


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    LOT_FULL = "lot_full"
    HIGH_OCCUPANCY = "high_occupancy"
    ANOMALY_DETECTED = "anomaly_detected"
    ZONE_FULL = "zone_full"
    DEMAND_SPIKE = "demand_spike"
    MAINTENANCE_REQUIRED = "maintenance_required"


class ParkingAlert:
    def __init__(self, alert_type, severity, message, lot_data=None):
        self.id = f"ALERT-{datetime.now().timestamp()}"
        self.type = alert_type
        self.severity = severity
        self.message = message
        self.timestamp = datetime.now()
        self.lot_data = lot_data
        self.acknowledged = False
        self.resolved = False
        
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type.value,
            'severity': self.severity.value,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'acknowledged': self.acknowledged,
            'resolved': self.resolved,
            'lot_occupancy': self.lot_data.get('occupancy_rate', 0) if self.lot_data else None
        }


class ParkingAlertEngine:
    def __init__(self, warning_threshold=75, critical_threshold=90):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.active_alerts = []
        self.alert_history = []
        self.last_occupancy = 0
        self.occupancy_trend = []
        self.max_trend_history = 20
        
    def check_alerts(self, lot_data):
        """Check for parking lot conditions that require alerts"""
        occupancy_rate = lot_data.get('occupancy_rate', 0)
        
        # Update trend
        self.occupancy_trend.append(occupancy_rate)
        if len(self.occupancy_trend) > self.max_trend_history:
            self.occupancy_trend.pop(0)
        
        # Check various conditions
        self._check_occupancy_alerts(occupancy_rate, lot_data)
        self._check_zone_alerts(lot_data)
        self._check_demand_spike(occupancy_rate, lot_data)
        
        # Clean up old alerts
        self._cleanup_old_alerts()
    
    def _check_occupancy_alerts(self, occupancy_rate, lot_data):
        """Check occupancy level and generate alerts"""
        # Remove previous occupancy alerts if conditions improved
        self.active_alerts = [a for a in self.active_alerts 
                             if a.type not in [AlertType.LOT_FULL, AlertType.HIGH_OCCUPANCY]]
        
        if occupancy_rate >= self.critical_threshold:
            # Check if alert already exists
            if not any(a.type == AlertType.LOT_FULL for a in self.active_alerts):
                alert = ParkingAlert(
                    AlertType.LOT_FULL,
                    AlertSeverity.CRITICAL,
                    f"🚨 CRITICAL: Parking lot is at {occupancy_rate:.1f}% capacity. Very few spots available.",
                    lot_data
                )
                self.active_alerts.append(alert)
                self.alert_history.append(alert)
                print(f"🚨 {alert.message}")
        
        elif occupancy_rate >= self.warning_threshold:
            # Check if alert already exists
            if not any(a.type == AlertType.HIGH_OCCUPANCY for a in self.active_alerts):
                alert = ParkingAlert(
                    AlertType.HIGH_OCCUPANCY,
                    AlertSeverity.WARNING,
                    f"⚠️ WARNING: Parking lot is at {occupancy_rate:.1f}% capacity. Getting full.",
                    lot_data
                )
                self.active_alerts.append(alert)
                self.alert_history.append(alert)
                print(f"⚠️ {alert.message}")
    
    def _check_zone_alerts(self, lot_data):
        """Check zone-specific conditions"""
        zone_stats = lot_data.get('zone_statistics', {})
        
        for zone, stats in zone_stats.items():
            zone_occupancy = stats.get('occupancy_rate', 0)
            
            if zone_occupancy >= 95:
                # Check if zone full alert already exists
                if not any(a.type == AlertType.ZONE_FULL and zone in a.message for a in self.active_alerts):
                    alert = ParkingAlert(
                        AlertType.ZONE_FULL,
                        AlertSeverity.WARNING,
                        f"⚠️ {zone} is full ({zone_occupancy:.1f}%). Recommend alternative zones.",
                        lot_data
                    )
                    self.active_alerts.append(alert)
                    self.alert_history.append(alert)
                    print(f"⚠️ {alert.message}")
    
    def _check_demand_spike(self, current_occupancy, lot_data):
        """Detect sudden demand spikes"""
        if len(self.occupancy_trend) >= 5:
            recent_avg = sum(self.occupancy_trend[-5:]) / 5
            previous_avg = sum(self.occupancy_trend[-10:-5]) / 5 if len(self.occupancy_trend) >= 10 else recent_avg
            
            # Detect spike (increase > 15%)
            spike_threshold = 15
            if (recent_avg - previous_avg) > spike_threshold:
                if not any(a.type == AlertType.DEMAND_SPIKE for a in self.active_alerts):
                    alert = ParkingAlert(
                        AlertType.DEMAND_SPIKE,
                        AlertSeverity.WARNING,
                        f"📈 Demand spike detected! Occupancy increased by {(recent_avg - previous_avg):.1f}%.",
                        lot_data
                    )
                    self.active_alerts.append(alert)
                    self.alert_history.append(alert)
                    print(f"📈 {alert.message}")
    
    def _cleanup_old_alerts(self):
        """Remove resolved or old alerts"""
        now = datetime.now()
        
        # Remove alerts older than 1 hour
        self.active_alerts = [
            a for a in self.active_alerts
            if (now - a.timestamp).total_seconds() < 3600
        ]
    
    def get_active_alerts(self):
        """Get all active, unresolved alerts"""
        return [a.to_dict() for a in self.active_alerts if not a.resolved]
    
    def get_alert_summary(self):
        """Get alert summary"""
        active = [a for a in self.active_alerts if not a.resolved]
        critical_count = len([a for a in active if a.severity == AlertSeverity.CRITICAL])
        warning_count = len([a for a in active if a.severity == AlertSeverity.WARNING])
        
        return {
            'total_active': len(active),
            'critical': critical_count,
            'warning': warning_count,
            'info': len([a for a in active if a.severity == AlertSeverity.INFO]),
            'timestamp': datetime.now().isoformat()
        }
    
    def acknowledge_alert(self, alert_id):
        """Acknowledge an alert"""
        for alert in self.active_alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    def resolve_alert(self, alert_id):
        """Resolve an alert"""
        for alert in self.active_alerts:
            if alert.id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                return True
        return False
    
    def get_alert_history(self, limit=50):
        """Get alert history"""
        return [a.to_dict() for a in self.alert_history[-limit:]]
    
    def get_statistics(self):
        """Get alert statistics"""
        total_alerts = len(self.alert_history)
        active = [a for a in self.active_alerts if not a.resolved]
        
        alert_type_counts = {}
        for alert in self.alert_history:
            alert_type = alert.type.value
            alert_type_counts[alert_type] = alert_type_counts.get(alert_type, 0) + 1
        
        return {
            'total_alerts_generated': total_alerts,
            'active_alerts': len(active),
            'critical_alerts': len([a for a in active if a.severity == AlertSeverity.CRITICAL]),
            'warning_alerts': len([a for a in active if a.severity == AlertSeverity.WARNING]),
            'alert_type_breakdown': alert_type_counts,
            'timestamp': datetime.now().isoformat()
        }


# Example usage
if __name__ == '__main__':
    alert_engine = ParkingAlertEngine(warning_threshold=75, critical_threshold=90)
    
    # Simulate parking lot data
    sample_data = {
        'occupancy_rate': 88.5,
        'occupied_spots': 159,
        'total_spots': 180,
        'zone_statistics': {
            'Zone-1': {'occupancy_rate': 92, 'occupied': 42, 'available': 3},
            'Zone-2': {'occupancy_rate': 85, 'occupied': 38, 'available': 7},
            'Zone-3': {'occupancy_rate': 88, 'occupied': 40, 'available': 5},
            'Zone-4': {'occupancy_rate': 82, 'occupied': 37, 'available': 8}
        }
    }
    
    # Check for alerts
    alert_engine.check_alerts(sample_data)
    
    # Get active alerts
    print("\n📋 Active Alerts:")
    for alert in alert_engine.get_active_alerts():
        print(f"  - [{alert['severity'].upper()}] {alert['message']}")
    
    # Get statistics
    stats = alert_engine.get_statistics()
    print(f"\n📊 Alert Statistics:")
    print(json.dumps(stats, indent=2))
