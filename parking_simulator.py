#!/usr/bin/env python3
"""
Smart Parking IoT System - Parking Spot Simulator
Simulates realistic parking lot with dynamic occupancy patterns
"""

import time
import random
import json
import threading
from datetime import datetime
from collections import defaultdict
import sqlite3

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
    def __init__(self, lot_id, zones=4, levels=3, spots_per_level=30):
        self.lot_id = lot_id
        self.zones = zones
        self.levels = levels
        self.spots_per_level = spots_per_level
        self.total_spots = zones * levels * spots_per_level
        self.spots = {}
        self.historical_occupancy = defaultdict(list)
        self.entry_exit_log = []
        self._initialize_spots()
        
    def _initialize_spots(self):
        """Initialize all parking spots"""
        spot_id = 0
        for zone in range(self.zones):
            for level in range(self.levels):
                for spot in range(self.spots_per_level):
                    self.spots[spot_id] = ParkingSpot(spot_id, f"Zone-{zone+1}", f"Level-{level+1}")
                    spot_id += 1
                    
    def get_random_spot(self):
        """Get a random available spot"""
        available = [s for s in self.spots.values() if not s.occupied]
        if available:
            return random.choice(available)
        return None
    
    def get_spots_by_zone(self, zone):
        """Get all spots in a zone"""
        return [s for s in self.spots.values() if s.zone == zone]
    
    def occupy_spot(self, spot_id, vehicle_type='car'):
        """Occupy a parking spot"""
        if spot_id in self.spots and not self.spots[spot_id].occupied:
            self.spots[spot_id].occupy(vehicle_type)
            self.entry_exit_log.append({
                'timestamp': datetime.now().isoformat(),
                'spot_id': spot_id,
                'event': 'entry',
                'vehicle_type': vehicle_type
            })
            return True
        return False
    
    def vacate_spot(self, spot_id):
        """Vacate a parking spot"""
        if spot_id in self.spots and self.spots[spot_id].occupied:
            occupancy_time = self.spots[spot_id].occupancy_time
            self.spots[spot_id].vacate()
            self.entry_exit_log.append({
                'timestamp': datetime.now().isoformat(),
                'spot_id': spot_id,
                'event': 'exit',
                'occupancy_duration': occupancy_time
            })
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
                for zone in [f"Zone-{i+1}" for i in range(self.zones)]
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def simulate_traffic(self):
        """Simulate parking lot traffic patterns"""
        # 5% chance of new vehicle arriving
        if random.random() < 0.05:
            spot = self.get_random_spot()
            if spot:
                vehicle_type = random.choice(['car', 'motorcycle', 'truck'])
                self.occupy_spot(spot.spot_id, vehicle_type)
        
        # Remove vehicles after random duration
        occupied_spots = [s for s in self.spots.values() if s.occupied]
        for spot in occupied_spots:
            spot.occupancy_time += 1
            # Average stay time: 45 minutes (2700 seconds), simulated in iterations
            if spot.occupancy_time > random.randint(30, 90):
                self.vacate_spot(spot.spot_id)
    
    def get_all_spots_status(self):
        """Get status of all parking spots"""
        return [s.get_status() for s in self.spots.values()]


class ParkingSimulator:
    def __init__(self, lot_id='PARKING-001'):
        self.parking_lot = ParkingLot(lot_id)
        self.running = False
        self.simulation_thread = None
        self.iteration_count = 0
        
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
        
    def stop_simulation(self):
        """Stop parking lot simulation"""
        self.running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=5)
        print("⛔ Parking simulator stopped")
        
    def _simulation_loop(self, interval):
        """Main simulation loop"""
        while self.running:
            self.parking_lot.simulate_traffic()
            self.iteration_count += 1
            time.sleep(interval)
    
    def get_lot_data(self):
        """Get current parking lot data"""
        stats = self.parking_lot.get_statistics()
        stats['iteration'] = self.iteration_count
        return stats
    
    def get_spot_details(self, spot_id):
        """Get details of a specific parking spot"""
        if spot_id in self.parking_lot.spots:
            return self.parking_lot.spots[spot_id].get_status()
        return None


# Example usage
if __name__ == '__main__':
    simulator = ParkingSimulator('LOT-001')
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
