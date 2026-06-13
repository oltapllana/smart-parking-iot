#!/usr/bin/env python3
"""
Smart Parking API Endpoints - Flask REST API
Provides endpoints for parking lot data, predictions, and management
"""

import sys

# Ensure emoji-laden logs don't crash the Windows (cp1252) console
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from flask import Flask, jsonify, request, render_template_string, g
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import os
import threading
import time

from parking_simulator import ParkingSimulator
from parking_ml_service import ParkingMLService
from parking_alert_engine import ParkingAlertEngine

# Use local pipeline (Kafka → Spark → Cassandra simulation)
from local_pipeline import get_components
from performance_monitor import get_monitor

try:
    from cassandra_client import CassandraClient
    HAS_CASSANDRA = True
except:
    HAS_CASSANDRA = False


app = Flask(__name__)
CORS(app)


@app.before_request
def _start_timer():
    g._start_time = time.time()


@app.after_request
def _record_latency(response):
    try:
        if hasattr(g, '_start_time'):
            latency_ms = (time.time() - g._start_time) * 1000.0
            get_monitor().record_api(latency_ms)
    except Exception:
        pass
    return response

# Global services
parking_simulator = None
ml_service = None
alert_engine = None
historical_data = []
MAX_HISTORY = 1000
kafka_queue = None
cassandra_db = None
spark_streamer = None
pipeline_mode = "LOCAL_FALLBACK"


def _env_flag(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_cassandra_settings():
    return {
        'use_real_cassandra': _env_flag('USE_REAL_CASSANDRA', False),
        'host': os.getenv('CASSANDRA_HOST', '127.0.0.1'),
        'port': int(os.getenv('CASSANDRA_PORT', '9042')),
        'keyspace': os.getenv('CASSANDRA_KEYSPACE', 'smart_parking'),
    }


def _empty_dashboard_payload(source='LOCAL_FALLBACK'):
    return {
        'source': source,
        'count': 0,
        'events': [],
        'timestamp': datetime.now().isoformat(),
    }


def _empty_window_payload(source='LOCAL_FALLBACK'):
    return {
        'source': source,
        'window_count': 0,
        'windows': [],
        'timestamp': datetime.now().isoformat(),
    }


def _get_dashboard_lot_data(lot_id='LOT-MAIN-001'):
    if pipeline_mode == 'REAL_CASSANDRA' and cassandra_db and hasattr(cassandra_db, 'get_latest_status_snapshot'):
        try:
            return cassandra_db.get_latest_status_snapshot(lot_id=lot_id)
        except Exception:
            return {}

    if parking_simulator:
        try:
            return parking_simulator.get_lot_data()
        except Exception:
            return {}

    return {}


def initialize_services():
    """Initialize all parking services"""
    global parking_simulator, ml_service, alert_engine
    global kafka_queue, cassandra_db, spark_streamer
    global pipeline_mode

    cassandra_settings = _get_cassandra_settings()
    use_real_cassandra = cassandra_settings['use_real_cassandra']

    if use_real_cassandra:
        pipeline_mode = 'REAL_CASSANDRA'
        print("🔥 Initializing REAL_CASSANDRA mode...")
        print(f"   Cassandra host={cassandra_settings['host']} port={cassandra_settings['port']} keyspace={cassandra_settings['keyspace']}")
        kafka_queue = None
        spark_streamer = None
        cassandra_db = None

        if HAS_CASSANDRA:
            try:
                cassandra_db = CassandraClient(
                    host=cassandra_settings['host'],
                    port=cassandra_settings['port'],
                    keyspace=cassandra_settings['keyspace'],
                )
                cassandra_db.connect()
                print("   ✅ REAL_CASSANDRA connected")
            except Exception as e:
                cassandra_db = None
                print(f"   ⚠️ REAL_CASSANDRA connection failed: {e}")
        else:
            print("   ⚠️ cassandra-driver not available; Cassandra API reads will return empty defaults")
    else:
        pipeline_mode = 'LOCAL_FALLBACK'
        print("🔥 Initializing LOCAL_FALLBACK mode...")
        kafka_queue, cassandra_db, spark_streamer = get_components()
        print("   ✅ Kafka simulator ready")
        print("   ✅ Spark streaming ready")
        print("   ✅ Cassandra database ready")

    print(f"   Pipeline mode: {pipeline_mode}")
    
    parking_simulator = ParkingSimulator('LOT-MAIN-001')
    parking_simulator.start_simulation(interval=2)
    
    ml_service = ParkingMLService()
    alert_engine = ParkingAlertEngine()
    
    # Start background data collection
    threading.Thread(target=collect_data, daemon=True).start()
    
    print("✅ All parking services initialized")


def collect_data():
    """Background thread to collect parking data periodically"""
    last_event_index = 0
    while True:
        try:
            if parking_simulator:
                data = parking_simulator.get_lot_data()
                historical_data.append(data)

                # Keep history under MAX_HISTORY
                if len(historical_data) > MAX_HISTORY:
                    historical_data.pop(0)

                if kafka_queue:
                    # 1) Drain the simulator's per-spot entry/exit events into
                    #    Kafka so Spark windowing/Cassandra see real sensor events.
                    log = parking_simulator.parking_lot.entry_exit_log
                    new_events = log[last_event_index:]
                    last_event_index = len(log)
                    for ev in new_events:
                        kafka_queue.produce('parking-events', ev, key=ev.get('lot_id'))

                    # 2) Periodic aggregate status_update event
                    status_event = {
                        'lot_id': data.get('lot_id'),
                        'timestamp': datetime.now().isoformat(),
                        'spot_id': 0,
                        'zone': 'ALL',
                        'level': 'ALL',
                        'event': 'status_update',
                        'occupied': data.get('occupied_spots', 0),
                        'vehicle_type': 'mixed',
                        'occupancy_duration': 0
                    }
                    kafka_queue.produce('parking-events', status_event, key=data.get('lot_id'))

                # Check for alerts
                alert_engine.check_alerts(data)
        except Exception as e:
            print(f"Error collecting data: {e}")

        time.sleep(5)  # Collect data every 5 seconds


# ========== API Endpoints ==========

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'simulator_running': parking_simulator.running if parking_simulator else False,
        'pipeline_mode': pipeline_mode,
    })


@app.route('/api/parking/status', methods=['GET'])
def get_parking_status():
    """Get current parking lot status"""
    lot_data = _get_dashboard_lot_data()
    analytics = {}

    if ml_service and lot_data:
        try:
            analytics = ml_service.get_analytics(lot_data, historical_data[-20:])
        except Exception:
            analytics = {}
    
    return jsonify({
        'lot_data': lot_data,
        'analytics': analytics,
        'source': pipeline_mode,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/parking/spots', methods=['GET'])
def get_all_spots():
    """Get all parking spot statuses"""
    if not parking_simulator:
        return jsonify({'error': 'Simulator not initialized'}), 500
    
    spots = parking_simulator.parking_lot.get_all_spots_status()
    return jsonify({
        'total_spots': len(spots),
        'spots': spots,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/parking/spot/<int:spot_id>', methods=['GET'])
def get_spot_detail(spot_id):
    """Get details of a specific parking spot"""
    if not parking_simulator:
        return jsonify({'error': 'Simulator not initialized'}), 500
    
    spot_status = parking_simulator.get_spot_details(spot_id)
    
    if not spot_status:
        return jsonify({'error': 'Spot not found'}), 404
    
    return jsonify({
        'spot': spot_status,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/parking/spot/<int:spot_id>/occupy', methods=['POST'])
def occupy_spot(spot_id):
    """Manually occupy a parking spot"""
    if not parking_simulator:
        return jsonify({'error': 'Simulator not initialized'}), 500
    
    vehicle_type = request.json.get('vehicle_type', 'car') if request.json else 'car'
    
    success = parking_simulator.parking_lot.occupy_spot(spot_id, vehicle_type)
    
    if success:
        return jsonify({
            'success': True,
            'message': f'Spot {spot_id} occupied',
            'spot': parking_simulator.get_spot_details(spot_id)
        })
    else:
        return jsonify({'success': False, 'error': 'Spot already occupied or invalid'}), 400


@app.route('/api/parking/spot/<int:spot_id>/vacate', methods=['POST'])
def vacate_spot(spot_id):
    """Manually vacate a parking spot"""
    if not parking_simulator:
        return jsonify({'error': 'Simulator not initialized'}), 500
    
    success = parking_simulator.parking_lot.vacate_spot(spot_id)
    
    if success:
        return jsonify({
            'success': True,
            'message': f'Spot {spot_id} vacated',
            'spot': parking_simulator.get_spot_details(spot_id)
        })
    else:
        return jsonify({'success': False, 'error': 'Spot not occupied or invalid'}), 400


@app.route('/api/parking/availability', methods=['GET'])
def get_availability():
    """Get parking availability prediction"""
    lot_data = _get_dashboard_lot_data()
    if not lot_data:
        return jsonify({
            'availability': 'HIGH',
            'confidence': 0,
            'occupancy_rate': 0,
            'recommendation': 'No live data available yet.',
            'model': 'rule-based-fallback',
            'timestamp': datetime.now().isoformat()
        })

    availability = ml_service.predict_availability(lot_data)
    
    return jsonify(availability)


@app.route('/api/parking/demand', methods=['GET'])
def get_demand_prediction():
    """Get parking demand prediction"""
    lot_data = _get_dashboard_lot_data()
    if not lot_data:
        return jsonify({
            'time_horizon': 30,
            'predicted_occupancy_rate': 0,
            'current_occupancy_rate': 0,
            'base_demand': 'LOW',
            'trend': 0,
            'trend_direction': 'stable',
            'demand_level': 'LOW',
            'model': 'rule-based-fallback',
            'timestamp': datetime.now().isoformat()
        })

    demand = ml_service.predict_demand(lot_data)
    
    return jsonify(demand)


@app.route('/api/parking/recommendations', methods=['GET'])
def get_zone_recommendations():
    """Get zone recommendations"""
    lot_data = _get_dashboard_lot_data()
    if not lot_data:
        return jsonify({'recommended_zone': None, 'alternatives': [], 'timestamp': datetime.now().isoformat()})

    recommendations = ml_service.recommend_alternative_zone(lot_data)
    
    return jsonify(recommendations)


@app.route('/api/parking/anomalies', methods=['GET'])
def detect_anomalies():
    """Detect anomalies in parking patterns"""
    lot_data = _get_dashboard_lot_data()
    if not lot_data:
        return jsonify({'anomaly_detected': 0, 'reason': 'no_data'})

    anomalies = ml_service.detect_anomalies(lot_data, historical_data[-50:])
    
    return jsonify(anomalies)


@app.route('/api/parking/alerts', methods=['GET'])
def get_alerts():
    """Get active alerts"""
    if not alert_engine:
        return jsonify({'error': 'Alert engine not initialized'}), 500
    
    alerts = alert_engine.get_active_alerts()
    
    return jsonify({
        'total_alerts': len(alerts),
        'alerts': alerts,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/parking/sms-status', methods=['GET'])
def sms_status():
    """Check whether SMS is currently usable."""
    if not alert_engine or not hasattr(alert_engine, 'sms'):
        return jsonify({'error': 'SMS service not initialized'}), 500

    return jsonify({
        'status': alert_engine.sms.status,
        'timestamp': datetime.now().isoformat(),
    })


@app.route('/api/parking/test-sms', methods=['POST'])
def test_sms():
    """Send a test SMS using the same critical-alert path."""
    if not alert_engine or not hasattr(alert_engine, 'sms'):
        return jsonify({'error': 'SMS service not initialized'}), 500

    payload = request.json or {}
    lot_id = payload.get('lot_id', 'LOT-TEST-001')
    occupancy = payload.get('occupancy', 92.0)

    result = alert_engine.sms.send_test_message(lot_id=lot_id, occupancy=float(occupancy))

    return jsonify({
        'success': result.get('sent', False),
        'result': result,
        'timestamp': datetime.now().isoformat(),
    }), (200 if result.get('sent', False) else 400)


@app.route('/api/parking/statistics', methods=['GET'])
def get_statistics():
    """Get parking statistics"""
    if not parking_simulator or not historical_data:
        return jsonify({'error': 'Not enough data'}), 500
    
    recent_data = historical_data[-100:]
    
    occupancy_rates = [d.get('occupancy_rate', 0) for d in recent_data]
    
    stats = {
        'current_occupancy': occupancy_rates[-1] if occupancy_rates else 0,
        'average_occupancy': sum(occupancy_rates) / len(occupancy_rates) if occupancy_rates else 0,
        'max_occupancy': max(occupancy_rates) if occupancy_rates else 0,
        'min_occupancy': min(occupancy_rates) if occupancy_rates else 0,
        'data_points': len(recent_data),
        'timestamp': datetime.now().isoformat()
    }
    
    return jsonify(stats)


@app.route('/api/parking/history', methods=['GET'])
def get_history():
    """Get occupancy history"""
    limit = request.args.get('limit', 100, type=int)

    if pipeline_mode == 'REAL_CASSANDRA' and cassandra_db and hasattr(cassandra_db, 'get_history'):
        try:
            history = cassandra_db.get_history(lot_id='LOT-MAIN-001', limit=limit)
        except Exception:
            history = []
    else:
        history = []
        for data in historical_data[-limit:]:
            history.append({
                'timestamp': data.get('timestamp'),
                'occupancy_rate': data.get('occupancy_rate', 0),
                'occupied_spots': data.get('occupied_spots', 0),
                'available_spots': data.get('available_spots', 0)
            })
    
    return jsonify({
        'history': history,
        'count': len(history)
    })


@app.route('/api/parking/zones', methods=['GET'])
def get_zones_info():
    """Get detailed information for all zones"""
    lot_data = _get_dashboard_lot_data()
    zone_stats = lot_data.get('zone_statistics', {})
    
    zones = []
    for zone_name, stats in zone_stats.items():
        zones.append({
            'name': zone_name,
            'occupancy_rate': stats.get('occupancy_rate', 0),
            'occupied_spots': stats.get('occupied', 0),
            'available_spots': stats.get('available', 0),
            'status': 'Full' if stats.get('occupancy_rate', 0) >= 90 else 'Available'
        })
    
    return jsonify({
        'zones': zones,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/parking/events', methods=['GET'])
def get_cassandra_events():
    """Get latest parking events from Cassandra"""
    lot_id = request.args.get('lot_id', 'LOT-MAIN-001')
    limit = request.args.get('limit', 20, type=int)

    try:
        if cassandra_db:
            events = cassandra_db.query(lot_id=lot_id, limit=limit)
        else:
            events = []

        return jsonify({
            'source': pipeline_mode,
            'lot_id': lot_id,
            'count': len(events),
            'events': events,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify(_empty_dashboard_payload(source=pipeline_mode))


@app.route('/api/parking/performance', methods=['GET'])
def get_performance():
    """Get real-time pipeline performance metrics (throughput, latency)."""
    snap = get_monitor().snapshot()

    # Augment with live pipeline stats
    if spark_streamer:
        try:
            snap['pipeline_stats'] = spark_streamer.get_stats()
        except Exception:
            pass

    return jsonify(snap)


@app.route('/api/parking/windows', methods=['GET'])
def get_windows():
    """Get Spark-style sliding-window aggregations of the event stream."""
    lot_id = request.args.get('lot_id', 'LOT-MAIN-001')
    limit = request.args.get('limit', 10, type=int)

    try:
        if spark_streamer:
            windows = spark_streamer.get_windows(limit=limit)
        elif cassandra_db and hasattr(cassandra_db, 'get_latest_window_stats'):
            windows = cassandra_db.get_latest_window_stats(lot_id=lot_id, limit=limit)
        else:
            windows = []
    except Exception:
        windows = []

    return jsonify({
        'window_count': len(windows),
        'windows': windows,
        'source': pipeline_mode,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/parking/ml-info', methods=['GET'])
def get_ml_info():
    """Get information about the trained ML models."""
    if not ml_service:
        return jsonify({'error': 'ML service not initialized'}), 500

    return jsonify({
        'model_info': ml_service.get_model_info(),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/parking/retrain', methods=['POST'])
def retrain_models():
    """Retrain the ML models.

    Body (JSON, optional):
      {"mode": "real"}      -> retrain on collected occupancy history
                               (blended with synthetic for robustness)
      {"mode": "synthetic"} -> retrain on freshly generated synthetic data
      {"samples": <int>}    -> synthetic sample count (synthetic mode)
    Defaults to real-data training, falling back to synthetic if there is
    not yet enough collected history.
    """
    if not ml_service:
        return jsonify({'error': 'ML service not initialized'}), 500

    body = request.json or {}
    mode = body.get('mode', 'real')

    if mode == 'real':
        result = ml_service.train_on_real_data(list(historical_data))
        if result.get('success'):
            return jsonify(result)
        # Not enough real data yet — fall back to synthetic so the call still
        # produces a usable model, and tell the caller why.
        n = body.get('samples', 4000)
        info = ml_service.train_on_synthetic_data(n_samples=n)
        return jsonify({
            'success': True,
            'mode': 'synthetic (fallback)',
            'note': result.get('reason'),
            'model_info': info,
        })

    n = body.get('samples', 4000)
    info = ml_service.train_on_synthetic_data(n_samples=n)
    return jsonify({'success': True, 'mode': 'synthetic', 'model_info': info})


@app.route('/', methods=['GET'])
def index():
    """Dashboard redirect"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Smart Parking IoT</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
            h1 { color: #333; }
            .endpoint { background: #f9f9f9; padding: 10px; margin: 10px 0; border-left: 4px solid #007bff; }
            code { background: #e9ecef; padding: 2px 6px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🅿️ Smart Parking IoT System - API</h1>
            <p>Real-time parking lot management and predictions</p>
            
            <h2>Available Endpoints</h2>
            <div class="endpoint">
                <strong>GET /api/health</strong> - System health check
            </div>
            <div class="endpoint">
                <strong>GET /api/parking/status</strong> - Current parking lot status with analytics
            </div>
            <div class="endpoint">
                <strong>GET /api/parking/spots</strong> - All parking spot statuses
            </div>
            <div class="endpoint">
                <strong>GET /api/parking/spot/&lt;id&gt;</strong> - Specific spot details
            </div>
            <div class="endpoint">
                <strong>POST /api/parking/spot/&lt;id&gt;/occupy</strong> - Occupy a spot
            </div>
            <div class="endpoint">
                <strong>POST /api/parking/spot/&lt;id&gt;/vacate</strong> - Vacate a spot
            </div>
            <div class="endpoint">
                <strong>GET /api/parking/availability</strong> - Availability prediction
            </div>
            <div class="endpoint">
                <strong>GET /api/parking/demand</strong> - Demand forecast
            </div>
            <div class="endpoint">
                <strong>GET /api/parking/recommendations</strong> - Zone recommendations
            </div>
            <div class="endpoint">
                <strong>GET /api/parking/alerts</strong> - Active alerts
            </div>
            <div class="endpoint">
                <strong>GET /api/parking/sms-status</strong> - SMS readiness check
            </div>
            <div class="endpoint">
                <strong>POST /api/parking/test-sms</strong> - Send a test SMS
            </div>
            <div class="endpoint">
                <strong>GET /api/parking/statistics</strong> - Parking statistics
            </div>
            <div class="endpoint">
                <strong>GET /api/parking/history</strong> - Occupancy history
            </div>
            <div class="endpoint">
                <strong>GET /api/parking/zones</strong> - Zone information
            </div>
        </div>
    </body>
    </html>
    '''


if __name__ == '__main__':
    initialize_services()
    print("🚀 Starting Smart Parking API Server")
    print("📍 Server running on http://localhost:5000")
    print("📊 API endpoints available at http://localhost:5000")
    # use_reloader=False: the reloader spawns a second process that would
    # start a duplicate simulator + Spark thread writing to the same DB.
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
