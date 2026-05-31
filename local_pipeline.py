#!/usr/bin/env python3
"""
Smart Parking Local Pipeline
Complete Kafka → Spark → Cassandra simulation without Docker
Perfect for development and demonstrations
"""

import json
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict, deque

import logging

from performance_monitor import get_monitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _parse_ts(ts):
    """Parse an ISO timestamp string to epoch seconds (best effort)."""
    if not ts:
        return time.time()
    try:
        return datetime.fromisoformat(ts).timestamp()
    except Exception:
        return time.time()


class LocalKafka:
    """File-based Kafka simulator"""
    
    def __init__(self, data_dir="local_data/kafka"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.topics = defaultdict(list)
        self.offsets = defaultdict(int)
        self.lock = threading.Lock()
        
    def produce(self, topic, message, key=None):
        """Send message to topic"""
        with self.lock:
            event = {
                'offset': len(self.topics[topic]),
                'timestamp': datetime.now().isoformat(),
                'key': key,
                'value': message
            }
            self.topics[topic].append(event)
            
            # Persist to file
            topic_file = self.data_dir / f"{topic}.jsonl"
            with open(topic_file, 'a') as f:
                f.write(json.dumps(event) + '\n')

            get_monitor().record_kafka()
            return True
    
    def consume(self, topic, from_offset=0, limit=None):
        """Read messages from topic"""
        with self.lock:
            messages = self.topics.get(topic, [])[from_offset:]
            if limit:
                messages = messages[:limit]
            return messages
    
    def get_latest(self, topic, limit=10):
        """Get latest N messages"""
        with self.lock:
            messages = self.topics.get(topic, [])
            return messages[-limit:] if messages else []
    
    def topic_count(self, topic):
        """Get message count for topic"""
        with self.lock:
            return len(self.topics.get(topic, []))


class LocalCassandra:
    """SQLite-based Cassandra simulator"""
    
    def __init__(self, db_path="local_data/cassandra.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()
        logger.info(f"✅ Local Cassandra initialized at {self.db_path}")
    
    def init_schema(self):
        """Create database schema"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parking_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_id TEXT,
                event_timestamp TEXT,
                spot_id INTEGER,
                zone TEXT,
                level TEXT,
                event TEXT,
                occupied BOOLEAN,
                vehicle_type TEXT,
                occupancy_duration INTEGER,
                processed_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_lot_timestamp 
            ON parking_events(lot_id, event_timestamp)
        ''')
        
        conn.commit()
        conn.close()
    
    def insert(self, event):
        """Insert event"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO parking_events 
            (lot_id, event_timestamp, spot_id, zone, level, event, occupied, vehicle_type, occupancy_duration, processed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.get('lot_id'),
            event.get('timestamp'),
            event.get('spot_id'),
            event.get('zone'),
            event.get('level'),
            event.get('event'),
            event.get('occupied', 0),
            event.get('vehicle_type'),
            event.get('occupancy_duration', 0),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def query(self, lot_id, limit=50):
        """Query events"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM parking_events 
            WHERE lot_id = ? 
            ORDER BY event_timestamp DESC 
            LIMIT ?
        ''', (lot_id, limit))
        
        columns = [d[0] for d in cursor.description or []]
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def count(self):
        """Get total events"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM parking_events')
        count = cursor.fetchone()[0]
        conn.close()
        return count


class SlidingWindowAggregator:
    """
    Spark-Streaming-style sliding/tumbling window aggregations.

    Groups processed events into fixed-size time windows and computes
    aggregates per window: event count, entries/exits, occupancy stats and
    vehicle-type distribution. This mirrors Spark's
    `groupBy(window(...)).agg(...)` semantics.
    """

    def __init__(self, window_seconds=60, max_windows=30):
        self.window_seconds = window_seconds
        self.windows = {}  # window_start_epoch -> aggregate dict
        self.max_windows = max_windows
        self.lock = threading.Lock()

    def add(self, event):
        ts = _parse_ts(event.get('timestamp'))
        window_start = int(ts // self.window_seconds) * self.window_seconds

        with self.lock:
            agg = self.windows.get(window_start)
            if agg is None:
                agg = {
                    'window_start': datetime.fromtimestamp(window_start).isoformat(),
                    'window_seconds': self.window_seconds,
                    'event_count': 0,
                    'entries': 0,
                    'exits': 0,
                    'status_updates': 0,
                    'occupancy_sum': 0,
                    'occupancy_samples': 0,
                    'max_occupied': 0,
                    'vehicle_types': defaultdict(int),
                }
                self.windows[window_start] = agg

            agg['event_count'] += 1
            etype = event.get('event')
            if etype == 'entry':
                agg['entries'] += 1
            elif etype == 'exit':
                agg['exits'] += 1
            elif etype == 'status_update':
                agg['status_updates'] += 1
                occ = event.get('occupied', 0)
                if isinstance(occ, (int, float)):
                    agg['occupancy_sum'] += occ
                    agg['occupancy_samples'] += 1
                    agg['max_occupied'] = max(agg['max_occupied'], occ)

            vt = event.get('vehicle_type')
            if vt and vt != 'mixed':
                agg['vehicle_types'][vt] += 1

            # Drop windows older than max_windows
            if len(self.windows) > self.max_windows:
                oldest = sorted(self.windows.keys())[:-self.max_windows]
                for k in oldest:
                    del self.windows[k]

    def get_windows(self, limit=10):
        with self.lock:
            keys = sorted(self.windows.keys(), reverse=True)[:limit]
            result = []
            for k in keys:
                agg = self.windows[k]
                avg_occ = (agg['occupancy_sum'] / agg['occupancy_samples']
                           if agg['occupancy_samples'] else 0)
                result.append({
                    'window_start': agg['window_start'],
                    'window_seconds': agg['window_seconds'],
                    'event_count': agg['event_count'],
                    'entries': agg['entries'],
                    'exits': agg['exits'],
                    'status_updates': agg['status_updates'],
                    'avg_occupied': round(avg_occ, 1),
                    'max_occupied': agg['max_occupied'],
                    'vehicle_types': dict(agg['vehicle_types']),
                })
            return result


class LocalSparkStreaming:
    """Simulates Spark Streaming processing with windowed aggregations."""

    def __init__(self, kafka, cassandra, window_seconds=60):
        self.kafka = kafka
        self.cassandra = cassandra
        self.running = False
        self.processed = 0
        self.lock = threading.Lock()
        self.aggregator = SlidingWindowAggregator(window_seconds=window_seconds)
        self.monitor = get_monitor()
        logger.info("✅ Local Spark Streaming initialized (windowed aggregations on)")

    def process_event(self, kafka_event):
        """Process + validate + enrich event (Spark transformation logic)."""
        message = kafka_event.get('value', {})

        # --- Validation / filtering (Spark .filter) ---
        valid = bool(message.get('lot_id')) and bool(message.get('timestamp'))
        data_quality = 0.95 if valid else 0.5

        processed = {
            **message,
            'spark_processed': True,
            'processed_timestamp': datetime.now().isoformat(),
            'data_quality': data_quality,
            'valid': valid,
        }
        return processed

    def run(self, interval=2):
        """Run stream processor (micro-batch loop)."""
        logger.info("🔥 Spark Streaming started")
        self.running = True
        last_offset = 0

        while self.running:
            try:
                events = self.kafka.consume('parking-events', from_offset=last_offset)

                for event in events:
                    processed = self.process_event(event)

                    # Sliding-window aggregation
                    self.aggregator.add(processed)

                    # End-to-end latency: produce time -> processed now
                    produced_at = _parse_ts(event.get('timestamp'))
                    latency_ms = max(0.0, (time.time() - produced_at) * 1000.0)
                    self.monitor.record_spark(latency_ms)

                    # Write to Cassandra (timed)
                    t0 = time.time()
                    self.cassandra.insert(processed)
                    self.monitor.record_cassandra((time.time() - t0) * 1000.0)

                    with self.lock:
                        self.processed += 1
                    last_offset += 1

                if events:
                    logger.info(f"✅ Processed {len(events)} events (total: {self.processed})")

                time.sleep(interval)

            except Exception as e:
                logger.error(f"Error: {e}")
                self.monitor.record_error()
                time.sleep(interval)

    def start_async(self, interval=2):
        """Start in background"""
        thread = threading.Thread(target=self.run, args=(interval,), daemon=True)
        thread.start()
        return thread

    def stop(self):
        """Stop processing"""
        self.running = False

    def get_windows(self, limit=10):
        """Get the latest windowed aggregations."""
        return self.aggregator.get_windows(limit)

    def get_stats(self):
        """Get processing stats"""
        with self.lock:
            return {
                'processed_events': self.processed,
                'cassandra_events': self.cassandra.count(),
                'kafka_messages': self.kafka.topic_count('parking-events')
            }


# Global instances
_kafka = None
_cassandra = None
_spark = None


def initialize():
    """Initialize full pipeline"""
    global _kafka, _cassandra, _spark
    
    _kafka = LocalKafka()
    _cassandra = LocalCassandra()
    _spark = LocalSparkStreaming(_kafka, _cassandra)
    _spark.start_async(interval=2)
    
    logger.info("✅ Local Pipeline Initialized")
    logger.info("   Kafka → Spark → Cassandra")
    
    return _kafka, _cassandra, _spark


def get_components():
    """Get pipeline components"""
    global _kafka, _cassandra, _spark
    
    if _kafka is None:
        initialize()
    
    return _kafka, _cassandra, _spark
