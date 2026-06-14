-- Smart Parking IoT - Cassandra schema
-- Applied automatically by the `cassandra-init` service in docker-compose.

CREATE KEYSPACE IF NOT EXISTS smart_parking
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE smart_parking;

-- Raw / processed sensor events written by Spark Streaming.
-- Partitioned by lot_id, clustered by event_timestamp (newest first) + spot_id.
-- `occupied` is stored as text because it is boolean for entry/exit events
-- and an integer count for status_update events.
CREATE TABLE IF NOT EXISTS parking_events (
    lot_id              text,
    event_timestamp     text,
    spot_id             int,
    zone                text,
    level               text,
    event               text,
    occupied            text,
    vehicle_type        text,
    occupancy_duration  int,
    data_quality        double,
    processed_timestamp text,
    PRIMARY KEY ((lot_id), event_timestamp, spot_id)
) WITH CLUSTERING ORDER BY (event_timestamp DESC, spot_id ASC);

-- Windowed aggregations produced by the Spark Streaming job
-- (event volume + entries/exits per 1-minute window).
CREATE TABLE IF NOT EXISTS parking_window_stats (
lot_id text,
window_start text,
window_end text,
event_count bigint,
entries bigint,
exits bigint,
avg_occupancy_duration double,
processed_timestamp text,
PRIMARY KEY ((lot_id), window_start)
) WITH CLUSTERING ORDER BY (window_start DESC);
