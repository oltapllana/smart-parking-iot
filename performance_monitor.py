#!/usr/bin/env python3
"""
Performance Analysis & Optimization module.

Collects real runtime metrics for the IoT pipeline:
  - throughput (events/sec) for Kafka, Spark and Cassandra stages
  - end-to-end and per-stage latency (with percentiles)
  - API request latency
  - rolling counters and uptime

Thread-safe; designed to be updated from the streaming threads and read
from Flask request handlers.
"""

import threading
import time
from collections import deque
from datetime import datetime
from statistics import mean


class _Stage:
    """Tracks counters + latency samples for a single pipeline stage."""

    def __init__(self, name, max_samples=500):
        self.name = name
        self.count = 0
        self.latencies = deque(maxlen=max_samples)   # milliseconds
        self.timestamps = deque(maxlen=max_samples)  # event wall-clock times

    def record(self, latency_ms=None):
        self.count += 1
        self.timestamps.append(time.time())
        if latency_ms is not None:
            self.latencies.append(latency_ms)

    def throughput(self, window_seconds=10):
        """Events per second over the recent window."""
        if not self.timestamps:
            return 0.0
        now = time.time()
        recent = [t for t in self.timestamps if now - t <= window_seconds]
        if len(recent) < 2:
            return round(len(recent) / window_seconds, 3)
        return round(len(recent) / window_seconds, 3)

    def latency_stats(self):
        if not self.latencies:
            return {'avg_ms': 0, 'min_ms': 0, 'max_ms': 0, 'p95_ms': 0, 'samples': 0}
        data = sorted(self.latencies)
        n = len(data)
        p95 = data[min(n - 1, int(0.95 * n))]
        return {
            'avg_ms': round(mean(data), 2),
            'min_ms': round(data[0], 2),
            'max_ms': round(data[-1], 2),
            'p95_ms': round(p95, 2),
            'samples': n
        }


class PerformanceMonitor:
    def __init__(self):
        self._lock = threading.Lock()
        self.start_time = time.time()
        self.stages = {
            'kafka': _Stage('kafka'),
            'spark': _Stage('spark'),
            'cassandra': _Stage('cassandra'),
            'api': _Stage('api'),
        }
        self.errors = 0

    # -- recording -----------------------------------------------------
    def record_kafka(self):
        with self._lock:
            self.stages['kafka'].record()

    def record_spark(self, latency_ms=None):
        with self._lock:
            self.stages['spark'].record(latency_ms)

    def record_cassandra(self, latency_ms=None):
        with self._lock:
            self.stages['cassandra'].record(latency_ms)

    def record_api(self, latency_ms):
        with self._lock:
            self.stages['api'].record(latency_ms)

    def record_error(self):
        with self._lock:
            self.errors += 1

    # -- reading -------------------------------------------------------
    def snapshot(self):
        with self._lock:
            uptime = time.time() - self.start_time
            kafka = self.stages['kafka']
            spark = self.stages['spark']
            cassandra = self.stages['cassandra']
            api = self.stages['api']

            spark_lat = spark.latency_stats()
            cass_lat = cassandra.latency_stats()
            api_lat = api.latency_stats()

            # End-to-end latency = produce -> stored in Cassandra
            end_to_end = spark_lat['avg_ms']

            total_processed = spark.count
            error_rate = (self.errors / total_processed * 100) if total_processed else 0

            return {
                'uptime_seconds': round(uptime, 1),
                'throughput': {
                    'kafka_eps': kafka.throughput(),
                    'spark_eps': spark.throughput(),
                    'cassandra_eps': cassandra.throughput(),
                },
                'latency': {
                    'end_to_end_ms': end_to_end,
                    'spark_processing': spark_lat,
                    'cassandra_write': cass_lat,
                    'api_response': api_lat,
                },
                'counters': {
                    'kafka_messages': kafka.count,
                    'spark_processed': spark.count,
                    'cassandra_events': cassandra.count,
                    'api_requests': api.count,
                    'errors': self.errors,
                },
                'health': {
                    'error_rate_pct': round(error_rate, 2),
                    'data_quality_pct': round(max(0, 100 - error_rate), 2),
                    'status': 'healthy' if error_rate < 5 else 'degraded',
                },
                'timestamp': datetime.now().isoformat(),
            }


# Global singleton shared across the pipeline + API
_monitor = None
_monitor_lock = threading.Lock()


def get_monitor():
    global _monitor
    if _monitor is None:
        with _monitor_lock:
            if _monitor is None:
                _monitor = PerformanceMonitor()
    return _monitor
