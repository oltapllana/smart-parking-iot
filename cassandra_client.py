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
            rows = list(self.session.execute(query, (lot_id, limit)))
            result = []
            for r in rows:
                if isinstance(r, dict):
                    result.append(r)
                else:
                    try:
                        result.append(dict(r._asdict()))
                    except Exception:
                        try:
                            result.append(dict(r))
                        except Exception:
                            result.append({k: str(v) for k, v in getattr(r, '__dict__', {}).items()})
            return result
        except Exception as e:
            print(f"⚠️ Cassandra query failed: {e}")
            raise

    def get_latest_window_stats(self, lot_id="LOT-MAIN-001", limit=10):
        if not lot_id or not self.session:
            return []

        query = """
        SELECT lot_id, window_start, window_end, event_count, "entries", "exits",
               avg_occupancy_duration
        FROM parking_window_stats
        WHERE lot_id = %s
        LIMIT %s
        """
        try:
            rows = list(self.session.execute(query, (lot_id, limit)))
            result = []
            for r in rows:
                if isinstance(r, dict):
                    result.append(r)
                else:
                    try:
                        result.append(dict(r._asdict()))
                    except Exception:
                        try:
                            result.append(dict(r))
                        except Exception:
                            result.append({k: str(v) for k, v in getattr(r, '__dict__', {}).items()})
            return result
        except Exception as e:
            print(f"⚠️ Cassandra window query failed: {e}")
            raise

    def get_latest_status_snapshot(self, lot_id="LOT-MAIN-001", total_spots=360, limit=50):
        # Build top-level snapshot and per-zone aggregates from recent events
        rows = self.get_latest_events(lot_id=lot_id, limit=max(limit * 3, limit))

        # Look for a status_update row for overall numbers
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

        # Aggregate per-zone occupancy using the most recent events
        zone_stats = {}
        # events may include per-spot entries/exits; count latest known occupied per spot per zone
        try:
            # We'll collect latest event per spot_id to infer occupied spots per zone
            latest_per_spot = {}
            for r in rows:
                spot = r.get('spot_id')
                if spot is None:
                    continue
                # prefer status_update timestamps if present
                ts = r.get('event_timestamp') or r.get('timestamp')
                # store latest by timestamp (string compare approx OK for ISO timestamps)
                prev = latest_per_spot.get(spot)
                if not prev or (ts and prev.get('ts') and ts > prev.get('ts')) or (ts and not prev.get('ts')):
                    latest_per_spot[spot] = {'row': r, 'ts': ts}

            # Count occupied per zone (ignore 'ALL' and unknown placeholders)
            zone_counts = {}
            for info in latest_per_spot.values():
                r = info['row']
                zone = r.get('zone') or 'UNKNOWN'
                if not zone or str(zone).upper() == 'ALL' or str(zone).upper() == 'UNKNOWN':
                    continue
                try:
                    event = str(r.get('event') or '')
                except Exception:
                    event = ''
                # Interpret events: 'occupy' or 'entry' or status_update with occupied field
                occupied_flag = 0
                if event in ('occupy', 'entry', 'status_update'):
                    # status_update may carry occupied snapshot; otherwise treat occupy/entry as 1
                    if event == 'status_update':
                        try:
                            occ = int(r.get('occupied') or 0)
                            # distribute unknown across zones roughly (skip distribution)
                            # we'll still set overall occupied above; for zones, use spot-level flags
                            occupied_flag = 0
                        except Exception:
                            occupied_flag = 0
                    else:
                        occupied_flag = 1
                elif event in ('vacate', 'exit'):
                    occupied_flag = 0
                else:
                    # unknown event types — try to infer from occupied field
                    try:
                        if int(r.get('occupied') or 0) > 0:
                            occupied_flag = 1
                    except Exception:
                        occupied_flag = 0

                zone_counts[zone] = zone_counts.get(zone, 0) + occupied_flag

            # Build zone statistics dict
            num_zones = len(zone_counts) if zone_counts else 0
            spots_per_zone = int(total_spots / num_zones) if num_zones else total_spots
            for zone, occ_count in zone_counts.items():
                avail = max(0, spots_per_zone - occ_count)
                rate = (occ_count / spots_per_zone * 100.0) if spots_per_zone else 0
                zone_stats[zone] = {
                    'occupancy_rate': round(rate, 2),
                    'occupied': int(occ_count),
                    'available': int(avail)
                }
        except Exception as e:
            print(f"⚠️ zone aggregation failed: {e}")

        return {
            'lot_id': lot_id,
            'total_spots': total_spots,
            'occupied_spots': occupied,
            'available_spots': available,
            'occupancy_rate': occupancy_rate,
            'zone_statistics': zone_stats,
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

    def count_events(self, lot_id="LOT-MAIN-001"):
        if not self.session:
            return 0
        try:
            q = "SELECT count(*) FROM parking_events WHERE lot_id = %s"
            row = self.session.execute(q, (lot_id,)).one()
            if not row:
                return 0
            # dict_factory returns a dict like {'count': X}
            if isinstance(row, dict):
                # try common keys
                for key in ('count', 'count(1)', 'system.count'):
                    if key in row:
                        return int(row.get(key) or 0)
                # fallback to first value
                try:
                    return int(next(iter(row.values())) or 0)
                except Exception:
                    return 0
            # for namedtuple / tuple-like
            try:
                return int(row[0])
            except Exception:
                try:
                    return int(getattr(row, 'count', 0) or 0)
                except Exception:
                    return 0
        except Exception as e:
            print(f"⚠️ Cassandra count_events failed: {e}")
            return 0

    def count_window_stats(self, lot_id="LOT-MAIN-001"):
        if not self.session:
            return 0
        try:
            q = "SELECT count(*) FROM parking_window_stats WHERE lot_id = %s"
            row = self.session.execute(q, (lot_id,)).one()
            if not row:
                return 0
            if isinstance(row, dict):
                for key in ('count', 'count(1)', 'system.count'):
                    if key in row:
                        return int(row.get(key) or 0)
                try:
                    return int(next(iter(row.values())) or 0)
                except Exception:
                    return 0
            try:
                return int(row[0])
            except Exception:
                try:
                    return int(getattr(row, 'count', 0) or 0)
                except Exception:
                    return 0
        except Exception as e:
            print(f"⚠️ Cassandra count_window_stats failed: {e}")
            return 0

    def close(self):
        if self.cluster:
            self.cluster.shutdown()