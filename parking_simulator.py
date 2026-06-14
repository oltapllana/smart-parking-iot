#!/usr/bin/env python3
"""
Smart Parking IoT System - Parking Spot Simulator
Simulates realistic parking lot with dynamic occupancy patterns
"""

import time
import math
import random
import json
import threading
from datetime import datetime
from collections import defaultdict
import sqlite3

try:
    from kafka_producer import ParkingKafkaProducer
except ImportError:
    ParkingKafkaProducer = None

class ParkingSpot:
    def __init__(self, spot_id, zone, level):
        self.spot_id = spot_id
        self.zone = zone
        self.level = level
        self.occupied = False
        self.occupancy_time = 0
        self.vehicle_type = None
        self.last_updated = datetime.now()
        
    def occupy(self, vehicle_type='car'):
        """Mark parking spot as occupied"""
        self.occupied = True
        self.occupancy_time = 0
        self.vehicle_type = vehicle_type
        self.last_updated = datetime.now()
        
    def vacate(self):
        """Mark parking spot as vacant"""
        self.occupied = False
        self.occupancy_time = 0
        self.vehicle_type = None
        self.last_updated = datetime.now()
        
    def get_status(self):
        """Get parking spot status"""
        return {
            'spot_id': self.spot_id,
            'zone': self.zone,
            'level': self.level,
            'occupied': self.occupied,
            'occupancy_time': self.occupancy_time,
            'vehicle_type': self.vehicle_type,
            'timestamp': self.last_updated.isoformat()
        }


class ParkingLot:
    def __init__(self, lot_id, zones=4, levels=3, spots_per_level=30, kafka_enabled=False,
                 demo_cycle_seconds=900):
        self.lot_id = lot_id
        self.zones = zones
        self.levels = levels
        self.spots_per_level = spots_per_level
        self.total_spots = zones * levels * spots_per_level
        self.spots = {}
        self.historical_occupancy = defaultdict(list)
        self.entry_exit_log = []

        # Demo traffic model: occupancy sweeps a full low->high->low cycle
        # over `demo_cycle_seconds` so the dashboard shows varied predictions
        # and the alert engine actually fires during a live demo.
        # Allow slower demo mode via environment vars to make debugging easier
        try:
            import os
            demo_slow = os.getenv('DEMO_SLOW_MODE', '').strip().lower() in {'1', 'true', 'yes', 'on'}
            if demo_slow:
                # Respect explicit interval override
                demo_cycle_seconds = int(os.getenv('DEMO_EVENT_INTERVAL_SECONDS', demo_cycle_seconds))
                # Limit maximum step to keep occupancy changes small
                self._demo_occupancy_change_limit = int(os.getenv('DEMO_OCCUPANCY_CHANGE_LIMIT', 1))
            else:
                self._demo_occupancy_change_limit = max(1, int(self.total_spots // 40))
        except Exception:
            self._demo_occupancy_change_limit = max(1, int(self.total_spots // 40))

        self.demo_cycle_seconds = demo_cycle_seconds
        self._sim_start = time.time()

        # External context that influences parking demand (drives the ML
        # weather/special-event features). Updated each tick from elapsed time.
        self.weather = 'clear'
        self.special_event = False

        self.kafka_enabled = kafka_enabled
        self.kafka_producer = None

        if self.kafka_enabled and ParkingKafkaProducer:
            try:
                self.kafka_producer = ParkingKafkaProducer()
                print("✅ Kafka producer connected")
            except Exception as e:
                print(f"⚠️ Kafka producer not connected: {e}")

        self._initialize_spots()

    def _initialize_spots(self):
        """Initialize all parking spots"""
        spot_id = 0
        for zone in range(self.zones):
            for level in range(self.levels):
                for spot in range(self.spots_per_level):
                    self.spots[spot_id] = ParkingSpot(
                        spot_id,
                        f"Zone-{zone + 1}",
                        f"Level-{level + 1}"
                    )
                    spot_id += 1

    def send_kafka_event(self, event):
        """Send parking event to Kafka if Kafka is enabled"""
        if self.kafka_producer:
            try:
                self.kafka_producer.send_event(event)
            except Exception as e:
                print(f"⚠️ Failed to send Kafka event: {e}")

    def get_random_spot(self):
        """Get a random available spot"""
        available = [s for s in self.spots.values() if not s.occupied]
        if available:
            return random.choice(available)
        return None

    def get_spots_by_zone(self, zone):
        """Get all spots in a zone"""
        return [s for s in self.spots.values() if s.zone == zone]
    # when an car enters to a parking spot, this creates an event and sends to Kafka
    def occupy_spot(self, spot_id, vehicle_type='car'):
        """Occupy a parking spot"""
        if spot_id in self.spots and not self.spots[spot_id].occupied:
            self.spots[spot_id].occupy(vehicle_type)
            spot = self.spots[spot_id]

            event = {
                'lot_id': self.lot_id,
                'timestamp': datetime.now().isoformat(),
                'spot_id': spot_id,
                'zone': spot.zone,
                'level': spot.level,
                'event': 'entry',
                'occupied': True,
                'vehicle_type': vehicle_type
            }

            self.entry_exit_log.append(event)
            self.send_kafka_event(event)

            return True
        return False
    # when an car exits from a parking spot, this creates an event and sends to Kafka
    def vacate_spot(self, spot_id):
        """Vacate a parking spot"""
        if spot_id in self.spots and self.spots[spot_id].occupied:
            occupancy_time = self.spots[spot_id].occupancy_time
            spot = self.spots[spot_id]

            event = {
                'lot_id': self.lot_id,
                'timestamp': datetime.now().isoformat(),
                'spot_id': spot_id,
                'zone': spot.zone,
                'level': spot.level,
                'event': 'exit',
                'occupied': False,
                'occupancy_duration': occupancy_time
            }

            self.spots[spot_id].vacate()
            self.entry_exit_log.append(event)
            self.send_kafka_event(event)

            return True
        return False

    def get_occupancy_rate(self):
        """Get current occupancy rate (0-100%)"""
        occupied = sum(1 for s in self.spots.values() if s.occupied)
        return (occupied / self.total_spots) * 100

    def get_zone_occupancy(self, zone):
        """Get occupancy rate for a specific zone"""
        zone_spots = self.get_spots_by_zone(zone)
        if not zone_spots:
            return 0
        occupied = sum(1 for s in zone_spots if s.occupied)
        return (occupied / len(zone_spots)) * 100

    def get_statistics(self):
        """Get parking lot statistics"""
        occupied_count = sum(1 for s in self.spots.values() if s.occupied)
        return {
            'lot_id': self.lot_id,
            'total_spots': self.total_spots,
            'occupied_spots': occupied_count,
            'available_spots': self.total_spots - occupied_count,
            'occupancy_rate': self.get_occupancy_rate(),
            'zone_statistics': {
                zone: {
                    'occupancy_rate': self.get_zone_occupancy(zone),
                    'occupied': sum(1 for s in self.get_spots_by_zone(zone) if s.occupied),
                    'available': sum(1 for s in self.get_spots_by_zone(zone) if not s.occupied)
                }
                for zone in [f"Zone-{i + 1}" for i in range(self.zones)]
            },
            'weather': self.weather,
            'special_event': self.special_event,
            'timestamp': datetime.now().isoformat()
        }

    # Extra demand (0..1) added by adverse weather — people drive more.
    WEATHER_BOOST = {'clear': 0.0, 'rain': 0.07, 'snow': 0.14}

    def _update_context(self, elapsed):
        """Update weather + special-event state so the demo visibly cycles
        through conditions that influence parking demand."""
        # Weather: mostly clear, with periodic rain/snow windows (~100s each)
        weather_cycle = ['clear', 'clear', 'rain', 'snow']
        self.weather = weather_cycle[int(elapsed // 100) % len(weather_cycle)]
        # Special event (match/concert nearby): active ~1 min every 4 min
        self.special_event = (int(elapsed // 60) % 4 == 3)

    def _target_occupancy_fraction(self):
        """Target occupancy (0..1) following a smooth daily-style cycle,
        nudged up by weather and special events."""
        elapsed = time.time() - self._sim_start
        self._update_context(elapsed)
        phase = (elapsed % self.demo_cycle_seconds) / self.demo_cycle_seconds
        # Cosine sweep: 0.10 (empty-ish) -> ~0.97 (full) -> 0.10
        wave = 0.5 - 0.5 * math.cos(2 * math.pi * phase)
        target = 0.10 + 0.87 * wave
        # External demand drivers
        target += self.WEATHER_BOOST.get(self.weather, 0.0)
        if self.special_event:
            target += 0.15
        target += random.uniform(-0.02, 0.02)  # small jitter
        return max(0.0, min(1.0, target))

    def simulate_traffic(self):
        """Simulate parking lot traffic driving occupancy toward a target."""
        occupied_spots = [s for s in self.spots.values() if s.occupied]
        current = len(occupied_spots)
        target = int(self._target_occupancy_fraction() * self.total_spots)
        diff = target - current

        # Gradual convergence so entries/exits stream realistically
        # Control how many spots may change per tick; in slow demo mode this will be small
        max_step = getattr(self, '_demo_occupancy_change_limit', max(1, self.total_spots // 40))

        if diff > 0:
            for _ in range(min(diff, max_step)):
                spot = self.get_random_spot()
                if spot:
                    vehicle_type = random.choices(
                        ['car', 'motorcycle', 'truck'], weights=[0.7, 0.2, 0.1])[0]
                    self.occupy_spot(spot.spot_id, vehicle_type)
        elif diff < 0:
            to_vacate = random.sample(occupied_spots, min(-diff, max_step))
            for spot in to_vacate:
                self.vacate_spot(spot.spot_id)

        # Age occupied spots
        for spot in self.spots.values():
            if spot.occupied:
                spot.occupancy_time += 1
        
    def get_all_spots_status(self):
        """Get status of all parking spots"""
        return [s.get_status() for s in self.spots.values()]

class ParkingSimulator:
    # Prepare simulator
    def __init__(self, lot_id='PARKING-001', kafka_enabled=False):
        self.parking_lot = ParkingLot(lot_id, kafka_enabled=kafka_enabled)
        self.running = False
        self.simulation_thread = None
        self.iteration_count = 0
    # start running
    def start_simulation(self, interval=1):
        """Start parking lot simulation"""
        self.running = True
        self.simulation_thread = threading.Thread(
            target=self._simulation_loop,
            args=(interval,),
            daemon=True
        )
        self.simulation_thread.start()
        print(f"✅ Parking simulator started for {self.parking_lot.lot_id}")
    # stop running  
    def stop_simulation(self):
        """Stop parking lot simulation"""
        self.running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=5)
        print("⛔ Parking simulator stopped")
    # repeat traffic changes 
    def _simulation_loop(self, interval):
        """Main simulation loop"""
        while self.running:
            self.parking_lot.simulate_traffic()
            self.iteration_count += 1
            time.sleep(interval)
    # get full parking summary
    def get_lot_data(self):
        """Get current parking lot data"""
        stats = self.parking_lot.get_statistics()
        stats['iteration'] = self.iteration_count
        return stats
    # get one parking spot info
    def get_spot_details(self, spot_id):
        """Get details of a specific parking spot"""
        if spot_id in self.parking_lot.spots:
            return self.parking_lot.spots[spot_id].get_status()
        return None


# Example usage
if __name__ == '__main__':
    # create simulator for 'LOT-001' with Kafka enabled, run every 0.5s
    simulator = ParkingSimulator('LOT-001', kafka_enabled=True)
    simulator.start_simulation(interval=0.5)
    
    try:
        for i in range(20):
            data = simulator.get_lot_data()
            print(f"\n[Iteration {data['iteration']}]")
            print(f"Occupancy: {data['occupancy_rate']:.1f}%")
            print(f"Occupied: {data['occupied_spots']}/{data['total_spots']}")
            print(f"Available: {data['available_spots']}")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n⛔ Shutting down...")
    finally:
        simulator.stop_simulation()
