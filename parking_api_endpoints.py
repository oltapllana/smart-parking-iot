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


def _build_debug(lot_data=None, endpoint=None, row_count_used=0):
    """Standard debug payload to attach to API responses for validation."""
    debug = {
        'endpoint': endpoint,
        'source': pipeline_mode,
        'fetched_at': datetime.now().isoformat(),
        'latest_event_timestamp': None,
        'row_count_used': int(row_count_used or 0),
        'total_spots': None,
        'occupied_spots': None,
        'available_spots': None,
        'occupancy_rate': None,
    }
    try:
        if isinstance(lot_data, dict):
            debug['total_spots'] = lot_data.get('total_spots')
            debug['occupied_spots'] = lot_data.get('occupied_spots')
            debug['available_spots'] = lot_data.get('available_spots')
            debug['occupancy_rate'] = lot_data.get('occupancy_rate')
            debug['latest_event_timestamp'] = lot_data.get('timestamp') or lot_data.get('event_timestamp')
    except Exception:
        pass
    return debug


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
    
    source_details = []
    if pipeline_mode == 'REAL_CASSANDRA':
        source_details.append('REAL_CASSANDRA')
    else:
        source_details.append('LOCAL_SIMULATOR')
    if ml_service:
        source_details.append('ML_SERVICE')

    # Normalize zone statistics so zone sums match overall snapshot
    try:
        total_spots = int(lot_data.get('total_spots') or 360)
        overall_occupied = int(min(int(lot_data.get('occupied_spots') or 0), total_spots))
        overall_available = max(0, total_spots - overall_occupied)
        zs = lot_data.get('zone_statistics') or {}
        # collect current per-zone occupied (allow both 'occupied' and 'occupied_spots')
        zone_items = []
        for zname, zstats in zs.items():
            occ = int(zstats.get('occupied') if 'occupied' in zstats else zstats.get('occupied_spots', 0) or 0)
            zone_items.append({'name': zname, 'occupied': occ})

        sum_zone_occ = sum(z['occupied'] for z in zone_items) if zone_items else 0
        if sum_zone_occ != overall_occupied and zone_items:
            # distribute difference proportionally to existing occupied or evenly if all zero
            diff = overall_occupied - sum_zone_occ
            if sum_zone_occ > 0:
                for z in zone_items:
                    add = int(round((z['occupied'] / sum_zone_occ) * diff))
                    z['occupied'] = max(0, min(90, z['occupied'] + add))
            else:
                # distribute evenly
                idx = 0
                while diff > 0:
                    zone_items[idx % len(zone_items)]['occupied'] += 1
                    diff -= 1
                    idx += 1

            # write back into lot_data.zone_statistics with capacity 90 per zone
            for z in zone_items:
                name = z['name']
                occ = int(min(max(z['occupied'], 0), int(total_spots / max(1, len(zone_items)))))
                avail = max(0, int(total_spots / max(1, len(zone_items))) - occ)
                rate = round((occ / max(1, int(total_spots / max(1, len(zone_items))))) * 100.0, 2)
                lot_data['zone_statistics'][name] = {
                    'occupancy_rate': rate,
                    'occupied': occ,
                    'available': avail
                }
        # ensure overall fields consistent
        lot_data['occupied_spots'] = overall_occupied
        lot_data['available_spots'] = overall_available
        lot_data['occupancy_rate'] = round((overall_occupied / total_spots) * 100.0, 2) if total_spots else 0.0
    except Exception:
        pass

    # Build debug payload (estimate row count if possible)
    row_est = 0
    try:
        if pipeline_mode == 'REAL_CASSANDRA' and cassandra_db and hasattr(cassandra_db, 'get_latest_events'):
            recent = cassandra_db.get_latest_events(limit=50)
            row_est = len(recent or [])
    except Exception:
        row_est = 0

    debug = _build_debug(lot_data=lot_data, endpoint='/api/parking/status', row_count_used=row_est)
    debug['source_details'] = source_details

    return jsonify({
        'lot_data': lot_data,
        'analytics': analytics,
        'debug': debug,
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
    availability['source'] = pipeline_mode
    availability['source_details'] = ('ML_SERVICE', 'REAL_CASSANDRA') if pipeline_mode == 'REAL_CASSANDRA' else ('ML_SERVICE', 'LOCAL_SIMULATOR')
    debug = _build_debug(lot_data=lot_data, endpoint='/api/parking/availability')
    availability['debug'] = debug
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
    demand['source'] = pipeline_mode
    demand['source_details'] = ('ML_SERVICE', 'REAL_CASSANDRA') if pipeline_mode == 'REAL_CASSANDRA' else ('ML_SERVICE', 'LOCAL_SIMULATOR')
    debug = _build_debug(lot_data=lot_data, endpoint='/api/parking/demand')
    demand['debug'] = debug
    return jsonify(demand)


@app.route('/api/parking/recommendations', methods=['GET'])
def get_zone_recommendations():
    """Get zone recommendations"""
    lot_data = _get_dashboard_lot_data()
    if not lot_data:
        return jsonify({'recommended_zone': None, 'alternatives': [], 'timestamp': datetime.now().isoformat()})

    recommendations = ml_service.recommend_alternative_zone(lot_data)
    recommendations['source'] = pipeline_mode
    recommendations['source_details'] = ('ML_SERVICE', 'REAL_CASSANDRA') if pipeline_mode == 'REAL_CASSANDRA' else ('ML_SERVICE', 'LOCAL_SIMULATOR')
    recommendations['debug'] = _build_debug(lot_data=lot_data, endpoint='/api/parking/recommendations')
    return jsonify(recommendations)


@app.route('/api/parking/anomalies', methods=['GET'])
def detect_anomalies():
    """Detect anomalies in parking patterns"""
    lot_data = _get_dashboard_lot_data()
    if not lot_data:
        return jsonify({'anomaly_detected': 0, 'reason': 'no_data'})

    # If running REAL_CASSANDRA and historical_data is empty, attempt to load from Cassandra
    hist = historical_data[-50:]
    if pipeline_mode == 'REAL_CASSANDRA' and cassandra_db and not hist:
        try:
            hist = cassandra_db.get_history(lot_id='LOT-MAIN-001', limit=200)
        except Exception as e:
            print(f"⚠️ /api/parking/anomalies failed to fetch history from Cassandra: {e}")

    anomalies = ml_service.detect_anomalies(lot_data, hist)
    anomalies['source'] = pipeline_mode
    anomalies['source_details'] = ('ML_SERVICE', 'REAL_CASSANDRA') if pipeline_mode == 'REAL_CASSANDRA' else ('ML_SERVICE', 'LOCAL_SIMULATOR')
    anomalies['debug'] = _build_debug(lot_data=lot_data, endpoint='/api/parking/anomalies')
    return jsonify(anomalies)


@app.route('/api/parking/alerts', methods=['GET'])
def get_alerts():
    """Get active alerts"""
    if not alert_engine:
        return jsonify({'error': 'Alert engine not initialized'}), 500
    
    alerts = alert_engine.get_active_alerts()
    debug = _build_debug(lot_data=None, endpoint='/api/parking/alerts', row_count_used=len(alerts))
    return jsonify({
        'total_alerts': len(alerts),
        'alerts': alerts,
        'debug': debug,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/parking/sms-status', methods=['GET'])
def sms_status():
    """Check whether SMS is currently usable."""
    if not alert_engine or not hasattr(alert_engine, 'sms'):
        return jsonify({'error': 'SMS service not initialized'}), 500

    debug = _build_debug(lot_data=None, endpoint='/api/parking/sms-status')
    return jsonify({
        'status': alert_engine.sms.status,
        'debug': debug,
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

    debug = _build_debug(lot_data=None, endpoint='/api/parking/test-sms')
    payload = {
        'success': result.get('sent', False),
        'result': result,
        'debug': debug,
        'timestamp': datetime.now().isoformat(),
    }
    return jsonify(payload), (200 if result.get('sent', False) else 400)


@app.route('/api/parking/statistics', methods=['GET'])
def get_statistics():
    """Get parking statistics"""
    # Prefer Cassandra history in REAL_CASSANDRA mode so dashboard shows real stats
    if pipeline_mode == 'REAL_CASSANDRA' and cassandra_db:
        try:
            hist = cassandra_db.get_history(lot_id='LOT-MAIN-001', limit=200)
            occupancy_rates = [h.get('occupancy_rate', 0) for h in hist]
            stats = {
                'current_occupancy': occupancy_rates[-1] if occupancy_rates else 0,
                'average_occupancy': sum(occupancy_rates) / len(occupancy_rates) if occupancy_rates else 0,
                'max_occupancy': max(occupancy_rates) if occupancy_rates else 0,
                'min_occupancy': min(occupancy_rates) if occupancy_rates else 0,
                'data_points': len(occupancy_rates),
                'source': 'REAL_CASSANDRA',
                'timestamp': datetime.now().isoformat()
            }
            stats['debug'] = _build_debug(lot_data=None, endpoint='/api/parking/statistics', row_count_used=len(occupancy_rates))
            return jsonify(stats)
        except Exception as e:
            print(f"⚠️ /api/parking/statistics cassandra query failed: {e}")
            # fall through to simulator if Cassandra fails

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
        'source': 'LOCAL_FALLBACK',
        'timestamp': datetime.now().isoformat()
    }
    stats['debug'] = _build_debug(lot_data=None, endpoint='/api/parking/statistics', row_count_used=len(recent_data))
    return jsonify(stats)


@app.route('/api/parking/history', methods=['GET'])
def get_history():
    """Get occupancy history"""
    limit = request.args.get('limit', 100, type=int)
    total_spots = 360

    # Authoritative current snapshot (status) to be used as latest history point
    try:
        current_snapshot = _get_dashboard_lot_data()
    except Exception:
        current_snapshot = None

    history = []
    if pipeline_mode == 'REAL_CASSANDRA':
        if not cassandra_db:
            return jsonify({'error': 'REAL_CASSANDRA requested but Cassandra client not initialized'}), 500
        try:
            history = cassandra_db.get_history(lot_id='LOT-MAIN-001', limit=limit)
            # If no status_update rows, try to derive from window stats (avoid counting raw events)
            if not history and hasattr(cassandra_db, 'get_latest_window_stats'):
                wins = cassandra_db.get_latest_window_stats(lot_id='LOT-MAIN-001', limit=limit)
                for w in wins:
                    try:
                        avg_occ = float(w.get('avg_occupancy_duration') or 0)
                    except Exception:
                        avg_occ = 0
                    occ = int(round((avg_occ / 100.0) * total_spots))
                    history.append({
                        'timestamp': w.get('window_start'),
                        'occupancy_rate': min(max(avg_occ, 0.0), 100.0),
                        'occupied_spots': min(max(occ, 0), total_spots),
                        'available_spots': max(0, total_spots - min(max(occ, 0), total_spots))
                    })
        except Exception as e:
            print(f"⚠️ /api/parking/history cassandra query failed: {e}")
            return jsonify({'error': 'Failed to fetch history from Cassandra', 'details': str(e)}), 500
    else:
        for data in historical_data[-limit:]:
            occ = int(min(data.get('occupied_spots', 0), total_spots))
            occ_rate = float(min(data.get('occupancy_rate', 0), 100.0))
            avail = max(0, total_spots - occ)
            history.append({
                'timestamp': data.get('timestamp'),
                'occupancy_rate': occ_rate,
                'occupied_spots': occ,
                'available_spots': avail
            })

    # Ensure latest history point matches current status snapshot when available
    try:
        if current_snapshot and history:
            latest_point = {
                'timestamp': current_snapshot.get('timestamp'),
                'occupancy_rate': min(float(current_snapshot.get('occupancy_rate') or 0), 100.0),
                'occupied_spots': int(min(current_snapshot.get('occupied_spots') or 0, total_spots)),
                'available_spots': max(0, total_spots - int(min(current_snapshot.get('occupied_spots') or 0, total_spots)))
            }
            history[-1] = latest_point

        # Cap all history points defensively
        for h in history:
            h['occupied_spots'] = int(min(int(h.get('occupied_spots') or 0), total_spots))
            h['occupancy_rate'] = float(min(max(float(h.get('occupancy_rate') or 0), 0.0), 100.0))
            h['available_spots'] = int(max(0, total_spots - h['occupied_spots']))
    except Exception:
        pass

    debug = _build_debug(lot_data=None, endpoint='/api/parking/history', row_count_used=len(history))
    return jsonify({
        'history': history,
        'count': len(history),
        'debug': debug
    })



@app.route('/api/parking/zones', methods=['GET'])
def get_zones_info():
    """Get detailed information for all zones"""
    lot_data = _get_dashboard_lot_data()
    zone_stats = lot_data.get('zone_statistics', {})

    # Enforce zone capacity and ensure sums match overall snapshot
    total_spots = int(lot_data.get('total_spots') or 360)
    spots_per_zone = 90
    desired_total_occupied = int(min(int(lot_data.get('occupied_spots') or 0), total_spots))

    zones = []
    # Build initial zone list and cap values
    for zone_name, stats in zone_stats.items():
        occ = int(min(int(stats.get('occupied', 0) or 0), spots_per_zone))
        avail = int(min(int(stats.get('available', spots_per_zone - occ) or 0), spots_per_zone))
        rate = float(min(max(float(stats.get('occupancy_rate', 0) or 0), 0.0), 100.0))
        zones.append({
            'name': zone_name,
            'occupancy_rate': rate,
            'occupied_spots': occ,
            'available_spots': avail,
            'status': 'Full' if rate >= 90 else 'Available'
        })

    # Adjust sums so that sum(occupied_spots) == desired_total_occupied
    current_sum = sum(z['occupied_spots'] for z in zones)
    diff = desired_total_occupied - current_sum
    if diff != 0 and zones:
        # If we need to add occupied spots, distribute to zones with room
        if diff > 0:
            i = 0
            while diff > 0:
                z = zones[i % len(zones)]
                if z['occupied_spots'] < spots_per_zone:
                    z['occupied_spots'] += 1
                    z['available_spots'] = max(0, spots_per_zone - z['occupied_spots'])
                    diff -= 1
                i += 1
                # safety to avoid infinite loop
                if i > spots_per_zone * len(zones):
                    break
        else:
            # Need to remove occupied spots
            remove = -diff
            i = 0
            while remove > 0:
                z = zones[i % len(zones)]
                if z['occupied_spots'] > 0:
                    z['occupied_spots'] -= 1
                    z['available_spots'] = max(0, spots_per_zone - z['occupied_spots'])
                    remove -= 1
                i += 1
                if i > spots_per_zone * len(zones):
                    break

    # Recompute occupancy_rate after adjustments
    for z in zones:
        z['occupancy_rate'] = round((z['occupied_spots'] / spots_per_zone) * 100.0, 2)
    
    # attempt to include debug from lot_data
    debug = _build_debug(lot_data=lot_data, endpoint='/api/parking/zones', row_count_used=0)
    return jsonify({
        'zones': zones,
        'debug': debug,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/parking/events', methods=['GET'])
def get_cassandra_events():
    """Get latest parking events from Cassandra"""
    lot_id = request.args.get('lot_id', 'LOT-MAIN-001')
    limit = request.args.get('limit', 20, type=int)

    if pipeline_mode == 'REAL_CASSANDRA':
        if not cassandra_db:
            return jsonify({'error': 'REAL_CASSANDRA requested but Cassandra client not initialized'}), 500
        try:
            events = cassandra_db.query(lot_id=lot_id, limit=limit)
        except Exception as e:
            print(f"⚠️ /api/parking/events cassandra query failed: {e}")
            return jsonify({'error': 'Failed to fetch events from Cassandra', 'details': str(e)}), 500

        debug = _build_debug(lot_data=None, endpoint='/api/parking/events', row_count_used=len(events))
        return jsonify({
            'source': pipeline_mode,
            'lot_id': lot_id,
            'count': len(events),
            'events': events,
            'debug': debug,
            'timestamp': datetime.now().isoformat()
        })

    # Local fallback
    try:
        events = []
        debug = _build_debug(lot_data=None, endpoint='/api/parking/events', row_count_used=0)
        return jsonify({
            'source': pipeline_mode,
            'lot_id': lot_id,
            'count': 0,
            'events': events,
            'debug': debug,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"⚠️ /api/parking/events local fallback failed: {e}")
        return jsonify(_empty_dashboard_payload(source=pipeline_mode))


@app.route('/api/parking/performance', methods=['GET'])
def get_performance():
    """Get real-time pipeline performance metrics (throughput, latency)."""
    snap = get_monitor().snapshot()

    # If running in REAL_CASSANDRA, populate simple counters from Cassandra
    source_details = ['LOCAL_MONITOR']
    if pipeline_mode == 'REAL_CASSANDRA' and cassandra_db:
        try:
            cass_events = cassandra_db.count_events()
            cass_windows = cassandra_db.count_window_stats()
            snap['cassandra_events'] = cass_events
            snap['cassandra_window_count'] = cass_windows
            # Provide a non-zero indication for throughput summary
            snap['throughput']['cassandra_events'] = cass_events
            # If spark throughput is zero (no local monitor from Spark), derive a simple estimate
            try:
                if not snap['throughput'].get('spark_eps'):
                    uptime = snap.get('uptime_seconds') or 1
                    snap['throughput']['spark_eps'] = round(cass_events / max(1, uptime), 3)
            except Exception:
                pass
            source_details.append('REAL_CASSANDRA')
        except Exception as e:
            print(f"⚠️ /api/parking/performance cassandra counts failed: {e}")
    else:
        if pipeline_mode != 'REAL_CASSANDRA':
            source_details.append('LOCAL_PIPELINE')

    # Augment with live pipeline stats if available (local mode)
    if spark_streamer:
        try:
            snap['pipeline_stats'] = spark_streamer.get_stats()
            source_details.append('SPARK_STREAMER')
        except Exception as e:
            print(f"⚠️ spark_streamer.get_stats failed: {e}")

    snap['source_details'] = source_details
    debug = _build_debug(lot_data=None, endpoint='/api/parking/performance', row_count_used=(snap.get('cassandra_events') or 0))
    snap['debug'] = debug
    return jsonify(snap)


@app.route('/api/parking/windows', methods=['GET'])
def get_windows():
    """Get Spark-style sliding-window aggregations of the event stream."""
    lot_id = request.args.get('lot_id', 'LOT-MAIN-001')
    limit = request.args.get('limit', 10, type=int)

    if pipeline_mode == 'REAL_CASSANDRA':
        if not cassandra_db:
            return jsonify({'error': 'REAL_CASSANDRA requested but Cassandra client not initialized'}), 500
        try:
            windows = cassandra_db.get_latest_window_stats(lot_id=lot_id, limit=limit)
        except Exception as e:
            print(f"⚠️ /api/parking/windows cassandra query failed: {e}")
            return jsonify({'error': 'Failed to fetch windows from Cassandra', 'details': str(e)}), 500
    else:
        try:
            if spark_streamer:
                windows = spark_streamer.get_windows(limit=limit)
            else:
                windows = []
        except Exception as e:
            print(f"⚠️ /api/parking/windows local fetch failed: {e}")
            windows = []

    debug = _build_debug(lot_data=None, endpoint='/api/parking/windows', row_count_used=len(windows))
    return jsonify({
        'window_count': len(windows),
        'windows': windows,
        'source': pipeline_mode,
        'debug': debug,
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
