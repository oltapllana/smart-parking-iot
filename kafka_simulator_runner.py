#!/usr/bin/env python3
"""
Real-Kafka sensor simulator runner (for the Docker pipeline).

Runs the parking simulator with the real KafkaProducer enabled, streaming
entry/exit + periodic status_update events to the `parking-events` topic on
localhost:9092. Use this together with docker-compose (Kafka + Spark +
Cassandra) instead of the in-process local pipeline.

Usage:
    docker compose up -d          # start Kafka/Spark/Cassandra
    python kafka_simulator_runner.py
"""

import sys
import time
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from parking_simulator import ParkingSimulator
from kafka_producer import ParkingKafkaProducer


def main(lot_id='LOT-MAIN-001', status_interval=5):
    print("🚗 Starting Kafka sensor simulator -> topic 'parking-events' @ localhost:9092")

    # kafka_enabled=True makes every occupy/vacate emit an event to Kafka
    simulator = ParkingSimulator(lot_id, kafka_enabled=True)
    simulator.start_simulation(interval=0.5)

    # Separate producer for periodic aggregate status events
    status_producer = ParkingKafkaProducer()

    last_status = 0
    try:
        while True:
            now = time.time()
            if now - last_status >= status_interval:
                data = simulator.get_lot_data()
                status_event = {
                    'lot_id': data.get('lot_id'),
                    'timestamp': datetime.now().isoformat(),
                    'spot_id': 0,
                    'zone': 'ALL',
                    'level': 'ALL',
                    'event': 'status_update',
                    'occupied': data.get('occupied_spots', 0),
                    'vehicle_type': 'mixed',
                    'occupancy_duration': 0,
                }
                status_producer.send_event(status_event)
                print(f"📤 status_update — occupancy {data['occupancy_rate']:.1f}% "
                      f"({data['occupied_spots']}/{data['total_spots']})")
                last_status = now
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n⛔ Stopping simulator...")
        simulator.stop_simulation()


if __name__ == '__main__':
    main()
