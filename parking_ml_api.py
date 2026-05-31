#!/usr/bin/env python3
"""
Smart Parking ML API Service
Standalone Flask server on port 8090 that serves the trained ML models.
Called by the Spark Streaming job for real-time parking predictions.

Usage:
    python parking_ml_api.py

Endpoints:
    GET  /health           - service health + model status
    POST /predict          - single prediction
    POST /predict/batch    - batch predictions
    GET  /models/info      - model metadata
"""
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

from parking_ml_service import ParkingMLService

app = Flask(__name__)
CORS(app)

# Load / train models at startup
ml = ParkingMLService(auto_train=True)
print("✅ ML models ready")


def _build_lot_data(d: dict) -> dict:
    """Normalise a raw request dict into the shape ParkingMLService expects."""
    total = d.get('total_spots', 180)
    occupied = d.get('occupied_spots', int(total * d.get('occupancy_rate', 50) / 100))
    return {
        'occupancy_rate':  d.get('occupancy_rate', (occupied / total) * 100),
        'occupied_spots':  occupied,
        'available_spots': total - occupied,
        'total_spots':     total,
    }


@app.route('/health', methods=['GET'])
def health():
    info = ml.get_model_info()
    return jsonify({
        'status': 'ok',
        'model_trained': info.get('trained', False),
        'algorithm': info.get('algorithm', 'RandomForest'),
        'timestamp': datetime.now().isoformat(),
    })


@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json(force=True) or {}
    lot_data = _build_lot_data(data)
    result = ml.predict_availability(lot_data)
    result['timestamp'] = datetime.now().isoformat()
    return jsonify(result)


@app.route('/predict/batch', methods=['POST'])
def predict_batch():
    items = request.get_json(force=True) or []
    results = []
    for item in items:
        lot_data = _build_lot_data(item)
        r = ml.predict_availability(lot_data)
        r['timestamp'] = datetime.now().isoformat()
        results.append(r)
    return jsonify(results)


@app.route('/models/info', methods=['GET'])
def models_info():
    return jsonify(ml.get_model_info())


if __name__ == '__main__':
    print("🤖 Smart Parking ML API Service")
    print("   Listening on http://0.0.0.0:8090")
    app.run(host='0.0.0.0', port=8090, debug=False, use_reloader=False)
