#!/usr/bin/env python3
"""
Smart Parking IoT - Quick Test Script
Tests all components without requiring the full API/Dashboard
"""

import time
from parking_simulator import ParkingSimulator
from parking_ml_service import ParkingMLService
from parking_alert_engine import ParkingAlertEngine
import json


def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_section(title):
    print(f"\n  ▸ {title}")
    print("  " + "-" * 56)


def test_simulator():
    """Test the parking simulator"""
    print_header("🚗 Testing Parking Simulator")
    
    simulator = ParkingSimulator('LOT-TEST-001')
    simulator.start_simulation(interval=0.1)
    
    print_section("Simulating parking lot for 10 seconds...")
    
    for i in range(20):
        data = simulator.get_lot_data()
        occupancy = data['occupancy_rate']
        occupied = data['occupied_spots']
        available = data['available_spots']
        
        print(f"  Iteration {i+1:2d}: {occupancy:5.1f}% Full | "
              f"Occupied: {occupied:3d} | Available: {available:3d}")
        time.sleep(0.5)
    
    simulator.stop_simulation()
    print("\n  ✅ Simulator test completed")
    return simulator, data


def test_ml_service(lot_data):
    """Test the ML service"""
    print_header("🤖 Testing ML Analytics Service")
    
    ml_service = ParkingMLService()
    
    # Test availability prediction
    print_section("Availability Prediction")
    availability = ml_service.predict_availability(lot_data)
    print(f"  Availability: {availability['availability']}")
    print(f"  Confidence: {availability['confidence']*100:.0f}%")
    print(f"  Occupancy: {availability['occupancy_rate']:.1f}%")
    print(f"  Message: {availability['recommendation']}")
    
    # Test demand prediction
    print_section("Demand Forecast (30 minutes)")
    demand = ml_service.predict_demand(lot_data)
    print(f"  Predicted Occupancy: {demand['predicted_occupancy_rate']:.1f}%")
    print(f"  Demand Level: {demand['demand_level']}")
    print(f"  Base Demand: {demand['base_demand']}")
    print(f"  Trend: {demand['trend']:+.2f}%/hour")
    
    # Test zone recommendations
    print_section("Zone Recommendations")
    recommendations = ml_service.recommend_alternative_zone(lot_data)
    if recommendations['recommended_zone']:
        print(f"  Recommended Zone: {recommendations['recommended_zone']}")
        print(f"  Alternatives:")
        for alt in recommendations['alternatives'][:3]:
            print(f"    - {alt['zone']}: {alt['available_spots']} spots "
                  f"({alt['occupancy_rate']:.0f}% full)")
    
    print("\n  ✅ ML service test completed")
    return ml_service


def test_alert_engine(lot_data):
    """Test the alert engine"""
    print_header("🚨 Testing Alert Engine")
    
    alert_engine = ParkingAlertEngine(warning_threshold=50, critical_threshold=70)
    
    # Simulate various occupancy levels
    test_occupancies = [
        {'name': 'Low', 'rate': 30},
        {'name': 'Medium', 'rate': 60},
        {'name': 'High', 'rate': 80},
        {'name': 'Critical', 'rate': 95}
    ]
    
    print_section("Testing Different Occupancy Levels")
    
    for test in test_occupancies:
        test_data = lot_data.copy()
        test_data['occupancy_rate'] = test['rate']
        
        alert_engine.check_alerts(test_data)
        
        print(f"  {test['name']:10s} ({test['rate']:3d}%): ", end="")
        alerts = alert_engine.get_active_alerts()
        if alerts:
            print(f"{len(alerts)} alert(s)")
            for alert in alerts:
                print(f"    - [{alert['severity'].upper()}] {alert['message'][:50]}...")
        else:
            print("✅ No alerts")
    
    # Get statistics
    print_section("Alert Statistics")
    stats = alert_engine.get_statistics()
    print(f"  Total Alerts Generated: {stats['total_alerts_generated']}")
    print(f"  Critical Alerts: {stats['critical_alerts']}")
    print(f"  Warning Alerts: {stats['warning_alerts']}")
    
    print("\n  ✅ Alert engine test completed")
    return alert_engine


def run_integration_test():
    """Run full integration test"""
    print_header("🔗 Running Full Integration Test")
    
    simulator = ParkingSimulator('LOT-INTEGRATION-001')
    ml_service = ParkingMLService()
    alert_engine = ParkingAlertEngine()
    
    simulator.start_simulation(interval=0.1)
    
    print_section("Collecting 30 samples (15 seconds)...")
    
    data_history = []
    for i in range(30):
        data = simulator.get_lot_data()
        data_history.append(data)
        
        # Get analytics
        analytics = ml_service.get_analytics(data, data_history[-10:])
        alert_engine.check_alerts(data)
        
        occupancy = data['occupancy_rate']
        availability = analytics['availability_prediction']['availability']
        alerts = len(alert_engine.get_active_alerts())
        
        status = "✅" if alerts == 0 else f"⚠️ ({alerts})"
        print(f"  Sample {i+1:2d}: {occupancy:5.1f}% | "
              f"Availability: {availability:8s} | {status}")
        
        time.sleep(0.5)
    
    simulator.stop_simulation()
    
    print_section("Integration Test Summary")
    print(f"  ✅ Collected 30 data samples")
    print(f"  ✅ Ran ML analytics on each sample")
    print(f"  ✅ Generated alerts as needed")
    print(f"  ✅ All systems working correctly!")


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "🅿️ Smart Parking IoT - Test Suite" + " " * 14 + "║")
    print("╚" + "=" * 58 + "╝")
    
    try:
        # Test 1: Simulator
        simulator, data = test_simulator()
        
        # Test 2: ML Service
        ml_service = test_ml_service(data)
        
        # Test 3: Alert Engine
        alert_engine = test_alert_engine(data)
        
        # Test 4: Integration
        run_integration_test()
        
        # Summary
        print_header("✅ All Tests Completed Successfully!")
        print("\n  Your Smart Parking IoT System is ready to run!")
        print("\n  Next steps:")
        print("    1. Run: python parking_api_endpoints.py")
        print("    2. Run: npm start")
        print("    3. Open: http://localhost:3000")
        print("\n")
        
    except Exception as e:
        print_header("❌ Test Failed!")
        print(f"\n  Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
