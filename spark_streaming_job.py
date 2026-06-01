#!/usr/bin/env python3
"""
Apache Spark Structured Streaming job for the Smart Parking IoT pipeline.

Reads sensor events from Kafka, validates/enriches them, writes the raw
processed events to Cassandra AND computes 1-minute windowed aggregations
(event volume + entries/exits + average occupancy duration) written to a
second Cassandra table.

Run inside the `spark` container:

    docker exec -it smartparking-spark /opt/spark/bin/spark-submit \
      --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.6,\
com.datastax.spark:spark-cassandra-connector_2.12:3.5.1 \
      --conf spark.cassandra.connection.host=cassandra \
      /app/spark_streaming_job.py
"""

import urllib.request
import json as _json

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, to_timestamp, window, current_timestamp,
    count, sum as _sum, avg, when, lit, date_format
)
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType
)

# ML API Service URL (host.docker.internal resolves to the host from inside Docker)
ML_API_URL = "http://host.docker.internal:8090"


def _call_ml_api(occupancy_rate: float, occupied_spots: int, total_spots: int) -> dict:
    """Call the ML API service and return the prediction dict, or {} on failure."""
    payload = _json.dumps({
        'occupancy_rate': occupancy_rate,
        'occupied_spots': occupied_spots,
        'available_spots': total_spots - occupied_spots,
        'total_spots': total_spots,
    }).encode()
    req = urllib.request.Request(
        f"{ML_API_URL}/predict",
        data=payload,
        headers={'Content-Type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            return _json.loads(resp.read())
    except Exception:
        return {}


spark = (
    SparkSession.builder
    .appName("SmartParkingSparkStreaming")
    .config("spark.cassandra.connection.host", "cassandra")
    .config("spark.cassandra.connection.port", "9042")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

# occupied/vehicle_type kept as strings (occupied is bool OR int across event types)
schema = StructType([
    StructField("lot_id", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("spot_id", IntegerType(), True),
    StructField("zone", StringType(), True),
    StructField("level", StringType(), True),
    StructField("event", StringType(), True),
    StructField("occupied", StringType(), True),
    StructField("vehicle_type", StringType(), True),
    StructField("occupancy_duration", IntegerType(), True),
])

raw_stream = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "kafka:29092")
    .option("subscribe", "parking-events")
    .option("startingOffsets", "latest")
    .load()
)

parsed = (
    raw_stream
    .select(from_json(col("value").cast("string"), schema).alias("d"))
    .select("d.*")
    # Validation / filtering (drop events missing required fields)
    .filter(col("lot_id").isNotNull() & col("timestamp").isNotNull())
    .withColumn("event_time", to_timestamp(col("timestamp")))
)

# ---- 1) Raw processed events -> parking_events --------------------------
events_out = (
    parsed
    .withColumnRenamed("timestamp", "event_timestamp")
    .withColumn("data_quality", lit(0.95))
    .withColumn("processed_timestamp", date_format(current_timestamp(),
                                                   "yyyy-MM-dd'T'HH:mm:ss"))
    .select("lot_id", "event_timestamp", "spot_id", "zone", "level",
            "event", "occupied", "vehicle_type", "occupancy_duration",
            "data_quality", "processed_timestamp")
)


def write_events(batch_df, batch_id):
    n = batch_df.count()
    if n > 0:
        # --- ML API integration: predict on status_update events --------
        status_rows = batch_df.filter(col("event") == "status_update").limit(3).collect()
        for row in status_rows:
            try:
                occupied = int(row.occupied) if row.occupied and str(row.occupied).isdigit() else 0
                total = 360  # default lot capacity
                occupancy_rate = (occupied / total) * 100
                prediction = _call_ml_api(occupancy_rate, occupied, total)
                if prediction:
                    avail_class = prediction.get('availability_class', 'N/A')
                    confidence  = prediction.get('confidence', 0)
                    print(f"🤖 ML [{row.lot_id}] {avail_class} "
                          f"(conf {confidence:.0%}, occ {occupancy_rate:.1f}%)")
            except Exception:
                pass
        # ----------------------------------------------------------------

        (batch_df.write
         .format("org.apache.spark.sql.cassandra")
         .mode("append")
         .options(table="parking_events", keyspace="smart_parking")
         .save())
        print(f"✅ Batch {batch_id}: wrote {n} events to Cassandra")


events_query = (
    events_out.writeStream
    .foreachBatch(write_events)
    .outputMode("append")
    .option("checkpointLocation", "/tmp/chk_events")
    .start()
)

# ---- 2) Windowed aggregations -> parking_window_stats -------------------
windowed = (
    parsed
    .withWatermark("event_time", "2 minutes")
    .groupBy(col("zone"), window(col("event_time"), "1 minute"))
    .agg(
        count(lit(1)).alias("event_count"),
        _sum(when(col("event") == "entry", 1).otherwise(0)).alias("entry_count"),
        _sum(when(col("event") == "exit", 1).otherwise(0)).alias("exit_count"),
        avg(col("occupancy_duration")).alias("avg_occupancy_duration"),
    )
    .select(
        col("zone"),
        date_format(col("window.start"), "yyyy-MM-dd'T'HH:mm:ss").alias("window_start"),
        date_format(col("window.end"), "yyyy-MM-dd'T'HH:mm:ss").alias("window_end"),
        col("avg_occupancy_duration"),
        col("entry_count"),
        col("event_count"),
        col("exit_count"),
    )
)


def write_windows(batch_df, batch_id):
    if batch_df.count() > 0:
        (batch_df.write
         .format("org.apache.spark.sql.cassandra")
         .mode("append")
         .options(table="parking_window_stats", keyspace="smart_parking")
         .save())
        print(f"🪟 Batch {batch_id}: wrote {batch_df.count()} window aggregates")


windows_query = (
    windowed.writeStream
    .foreachBatch(write_windows)
    .outputMode("update")
    .option("checkpointLocation", "/tmp/chk_windows_v2")
    .start()
)

spark.streams.awaitAnyTermination()
