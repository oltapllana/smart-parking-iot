#!/usr/bin/env python3
"""
Performance benchmark for the Smart Parking IoT pipeline.

Drives the local Kafka -> Spark -> Cassandra pipeline with a configurable
event load and reports throughput, latency percentiles and per-stage timing.
Used for the "Performance Analysis & Optimization" section of the report.

Usage:
    python benchmark.py --events 2000 --rate 0
        (--rate 0 = produce as fast as possible)
"""

import argparse
import random
import sys
import time
from datetime import datetime

# Force UTF-8 so emoji-laden logs don't crash the Windows console
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from local_pipeline import initialize, get_components
from performance_monitor import get_monitor

ZONES = ['Zone-1', 'Zone-2', 'Zone-3', 'Zone-4']
LEVELS = ['Level-1', 'Level-2', 'Level-3']
VEHICLES = ['car', 'motorcycle', 'truck']
EVENTS = ['entry', 'exit', 'status_update']


def make_event(i):
    etype = random.choice(EVENTS)
    return {
        'lot_id': 'LOT-BENCH-001',
        'timestamp': datetime.now().isoformat(),
        'spot_id': random.randint(0, 359),
        'zone': random.choice(ZONES),
        'level': random.choice(LEVELS),
        'event': etype,
        'occupied': random.randint(0, 360) if etype == 'status_update' else (etype == 'entry'),
        'vehicle_type': random.choice(VEHICLES),
        'occupancy_duration': random.randint(0, 120),
    }


def run_benchmark(n_events, rate):
    print(f"\n🏁 Starting benchmark: {n_events} events "
          f"(rate={'unbounded' if rate == 0 else str(rate) + ' eps'})\n")

    kafka, cassandra, spark = initialize()
    monitor = get_monitor()

    cassandra_start = cassandra.count()
    t_start = time.time()

    for i in range(n_events):
        kafka.produce('parking-events', make_event(i), key='LOT-BENCH-001')
        if rate > 0:
            time.sleep(1.0 / rate)

    produce_elapsed = time.time() - t_start
    produce_eps = n_events / produce_elapsed if produce_elapsed else 0
    print(f"📤 Produced {n_events} events in {produce_elapsed:.2f}s "
          f"({produce_eps:.0f} events/sec into Kafka)")

    # Wait for Spark to drain the backlog into Cassandra
    print("⏳ Waiting for Spark to drain backlog into Cassandra...")
    target = cassandra_start + n_events
    drain_start = time.time()
    while cassandra.count() < target and (time.time() - drain_start) < 120:
        time.sleep(0.5)

    drain_elapsed = time.time() - drain_start
    processed = cassandra.count() - cassandra_start
    process_eps = processed / drain_elapsed if drain_elapsed else 0

    print(f"⚡ Spark processed {processed} events in {drain_elapsed:.2f}s "
          f"({process_eps:.0f} events/sec end-to-end)\n")

    snap = monitor.snapshot()
    print("=" * 60)
    print("📊 PERFORMANCE REPORT")
    print("=" * 60)
    print(f"Uptime:                 {snap['uptime_seconds']}s")
    print(f"Kafka messages:         {snap['counters']['kafka_messages']}")
    print(f"Spark processed:        {snap['counters']['spark_processed']}")
    print(f"Cassandra events:       {snap['counters']['cassandra_events']}")
    print(f"Errors:                 {snap['counters']['errors']}")
    print("-" * 60)
    print(f"Producer throughput:    {produce_eps:.0f} eps")
    print(f"End-to-end throughput:  {process_eps:.0f} eps")
    print("-" * 60)
    lat = snap['latency']
    print(f"End-to-end latency avg: {lat['spark_processing']['avg_ms']} ms")
    print(f"  p95:                  {lat['spark_processing']['p95_ms']} ms")
    print(f"  max:                  {lat['spark_processing']['max_ms']} ms")
    print(f"Cassandra write avg:    {lat['cassandra_write']['avg_ms']} ms")
    print(f"  p95:                  {lat['cassandra_write']['p95_ms']} ms")
    print("-" * 60)
    print(f"Data quality:           {snap['health']['data_quality_pct']}%")
    print(f"Status:                 {snap['health']['status']}")
    print("=" * 60)

    windows = spark.get_windows(limit=5)
    print(f"\n🪟 Latest {len(windows)} sliding windows "
          f"(window size = {windows[0]['window_seconds'] if windows else '?'}s):")
    for w in windows:
        print(f"  [{w['window_start']}] events={w['event_count']} "
              f"entries={w['entries']} exits={w['exits']} "
              f"avg_occupied={w['avg_occupied']}")

    return snap


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Smart Parking pipeline benchmark")
    parser.add_argument('--events', type=int, default=2000,
                        help='number of events to produce')
    parser.add_argument('--rate', type=int, default=0,
                        help='events per second (0 = unbounded)')
    args = parser.parse_args()

    run_benchmark(args.events, args.rate)
