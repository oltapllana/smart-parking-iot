from cassandra.cluster import Cluster
from cassandra.query import dict_factory


class CassandraClient:
    def __init__(self, host="127.0.0.1", port=9042, keyspace="smart_parking"):
        self.host = host
        self.port = port
        self.keyspace = keyspace
        self.cluster = None
        self.session = None

    def connect(self):
        self.cluster = Cluster([self.host], port=self.port)
        self.session = self.cluster.connect(self.keyspace)
        self.session.row_factory = dict_factory
        print("✅ Connected to Cassandra")

    def get_latest_events(self, lot_id="LOT-001", limit=20):
        query = """
        SELECT lot_id, event_timestamp, spot_id, zone, level, event,
               occupied, vehicle_type, occupancy_duration
        FROM parking_events
        WHERE lot_id = %s
        LIMIT %s
        """
        return list(self.session.execute(query, (lot_id, limit)))

    def close(self):
        if self.cluster:
            self.cluster.shutdown()