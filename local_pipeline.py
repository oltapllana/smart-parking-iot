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
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


class LocalSparkStreaming:
    """Simulates Spark Streaming processing"""
    
    def __init__(self, kafka, cassandra):
        self.kafka = kafka
        self.cassandra = cassandra
        self.running = False
        self.processed = 0
        self.lock = threading.Lock()
        logger.info("✅ Local Spark Streaming initialized")
    
    def process_event(self, kafka_event):
        """Process event (Spark logic)"""
        message = kafka_event.get('value', {})
        
        # Enrich with processing metadata
        processed = {
            **message,
            'spark_processed': True,
            'processed_timestamp': datetime.now().isoformat(),
            'data_quality': 0.95
        }
        
        return processed
    
    def run(self, interval=5):
        """Run stream processor"""
        logger.info("🔥 Spark Streaming started")
        self.running = True
        last_offset = 0
        
        while self.running:
            try:
                # Read from Kafka
                events = self.kafka.consume('parking-events', from_offset=last_offset)
                
                # Process and write to Cassandra
                for event in events:
                    processed = self.process_event(event)
                    self.cassandra.insert(processed)
                    
                    with self.lock:
                        self.processed += 1
                    
                    last_offset += 1
                
                if events:
                    logger.info(f"✅ Processed {len(events)} events (total: {self.processed})")
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(interval)
    
    def start_async(self, interval=5):
        """Start in background"""
        thread = threading.Thread(target=self.run, args=(interval,), daemon=True)
        thread.start()
        return thread
    
    def stop(self):
        """Stop processing"""
        self.running = False
    
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
