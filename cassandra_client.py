from importlib import import_module
from datetime import datetime


def _load_cassandra_driver():
    try:
        cluster_module = import_module('cassandra.cluster')
        query_module = import_module('cassandra.query')
        return cluster_module.Cluster, query_module.dict_factory
    except Exception:
        return None, None


Cluster, dict_factory = _load_cassandra_driver()


class CassandraClient:
    def __init__(self, host="127.0.0.1", port=9042, keyspace="smart_parking"):
        self.host = host
        self.port = port
        self.keyspace = keyspace
        self.cluster = None
        self.session = None

    def connect(self):
        if Cluster is None:
            raise RuntimeError("cassandra-driver is not installed")
        self.cluster = Cluster([self.host], port=self.port)
        self.session = self.cluster.connect(self.keyspace)
        if dict_factory is not None:
            self.session.row_factory = dict_factory
        print("✅ Connected to Cassandra")

    def get_latest_events(self, lot_id="LOT-001", limit=20):
        if not lot_id or not self.session:
            return []

        query = """
        SELECT lot_id, event_timestamp, spot_id, zone, level, event,
               occupied, vehicle_type, occupancy_duration
        FROM parking_events
        WHERE lot_id = %s
        LIMIT %s
        """
        try:
            return list(self.session.execute(query, (lot_id, limit)))
        except Exception:
            return []

    def get_latest_window_stats(self, lot_id="LOT-MAIN-001", limit=10):
        if not lot_id or not self.session:
            return []

        query = """
        SELECT lot_id, window_start, window_end, event_count, entries, exits,
               avg_occupancy_duration
        FROM parking_window_stats
        WHERE lot_id = %s
        LIMIT %s
        """
        try:
            return list(self.session.execute(query, (lot_id, limit)))
        except Exception:
            return []

    def get_latest_status_snapshot(self, lot_id="LOT-MAIN-001", total_spots=360, limit=50):
        rows = self.get_latest_events(lot_id=lot_id, limit=limit)
        latest_status = None

        for row in rows:
            if str(row.get('event')) == 'status_update':
                latest_status = row
                break

        occupied = 0
        timestamp = datetime.now().isoformat()
        if latest_status:
            try:
                occupied = int(latest_status.get('occupied') or 0)
            except Exception:
                occupied = 0
            timestamp = latest_status.get('event_timestamp') or latest_status.get('timestamp') or timestamp

        available = max(0, total_spots - occupied)
        occupancy_rate = (occupied / total_spots * 100.0) if total_spots else 0

        return {
            'lot_id': lot_id,
            'total_spots': total_spots,
            'occupied_spots': occupied,
            'available_spots': available,
            'occupancy_rate': occupancy_rate,
            'zone_statistics': {},
            'weather': 'clear',
            'special_event': False,
            'timestamp': timestamp,
        }

    def get_history(self, lot_id="LOT-MAIN-001", limit=100, total_spots=360):
        rows = self.get_latest_events(lot_id=lot_id, limit=max(limit * 3, limit))
        history_rows = [row for row in rows if str(row.get('event')) == 'status_update']
        history_rows.reverse()

        history = []
        for row in history_rows[-limit:]:
            try:
                occupied = int(row.get('occupied') or 0)
            except Exception:
                occupied = 0
            available = max(0, total_spots - occupied)
            occupancy_rate = (occupied / total_spots * 100.0) if total_spots else 0
            history.append({
                'timestamp': row.get('event_timestamp') or row.get('timestamp'),
                'occupancy_rate': occupancy_rate,
                'occupied_spots': occupied,
                'available_spots': available,
            })

        return history

    def query(self, lot_id="LOT-001", limit=20):
        return self.get_latest_events(lot_id=lot_id, limit=limit)

    def close(self):
        if self.cluster:
            self.cluster.shutdown()