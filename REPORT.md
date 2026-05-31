# Final Report — Smart Parking IoT System

**University of Prishtina "Hasan Prishtina"**
Faculty of Electrical and Computer Engineering
Course: Building an IoT System — Project 2

---

## 1. Introduction

### 1.1 Purpose
This project implements a complete IoT system for managing a smart parking lot.
The system collects data from (simulated) sensors, transmits it in real time via
**Apache Kafka**, processes it with **Apache Spark Streaming**, stores it in
**Apache Cassandra**, and visualizes it through a **React web dashboard**.

### 1.2 Objectives
- Collect parking sensor data (entry / exit / status).
- Transmit the data through Apache Kafka.
- Process it in real time with Apache Spark Streaming (validation, filtering,
  sliding-window aggregations).
- Store it in an organized way in Apache Cassandra.
- Provide an interactive visualization interface.
- **Advanced components:** Artificial Intelligence (ML predictions), an Alarm
  System, and Performance Analysis & Optimization.

---

## 2. Project Infrastructure (Architecture)

```
🚗 Sensors (Simulator: 360 spots, 4 zones × 3 levels × 30)
        │  entry / exit / status_update
        ▼
📡 Apache Kafka  (topic: parking-events)
        ▼
⚡ Apache Spark Streaming
     • validation & filtering
     • enrichment (data_quality, processed_timestamp)
     • sliding-window aggregations (1 min)
        ▼
💾 Apache Cassandra  (keyspace: smart_parking)
     • parking_events
     • parking_window_stats
        ▼
🌐 Flask REST API  ──▶  ⚛️ React Dashboard
        ▲
🤖 ML Service   🚨 Alert Engine   📊 Performance Monitor
```

### 2.1 Two execution modes
The system supports two configurations that share the same logic:

| Mode | Description | Use case |
|---|---|---|
| **Local pipeline** (`local_pipeline.py`) | Kafka/Spark/Cassandra simulated in-process (file-based + SQLite). | Fast, reliable demo without Docker. |
| **Docker pipeline** (`docker-compose.yml`) | Real Apache Kafka + Spark + Cassandra. | Production environment — see [DOCKER_PIPELINE.md](DOCKER_PIPELINE.md). |

### 2.2 Technologies
- **Backend:** Python, Flask, scikit-learn, kafka-python, cassandra-driver, PySpark
- **Frontend:** React 18, Recharts, styled-components, axios
- **Infrastructure:** Docker Compose (Kafka, Spark, Cassandra, Zookeeper)

---

## 3. Apache Kafka Integration

Sensors produce events to the `parking-events` topic. Each event looks like:

```json
{
  "lot_id": "LOT-MAIN-001",
  "timestamp": "2026-05-31T18:50:00",
  "spot_id": 142,
  "zone": "Zone-2",
  "level": "Level-1",
  "event": "entry",
  "occupied": true,
  "vehicle_type": "car",
  "occupancy_duration": 0
}
```

- **Producer:** `kafka_producer.py` (`ParkingKafkaProducer`) for Docker; the
  simulator calls it automatically when `kafka_enabled=True` (see
  `kafka_simulator_runner.py`).
- **Topic:** created automatically by the `kafka-init` service (3 partitions,
  replication factor 1).
- **Consumer:** Spark Streaming subscribes to `parking-events`.

In the local pipeline, the `LocalKafka` class stores messages in
`local_data/kafka/parking-events.jsonl` with the same produce/consume/offset
semantics.

---

## 4. Apache Spark Streaming Processing

The `spark_streaming_job.py` application (Structured Streaming):

1. **Reads** from Kafka (`kafka:29092`, topic `parking-events`).
2. **Parse + Validation:** deserializes JSON against the schema and filters out
   events missing `lot_id`/`timestamp` (`.filter(...)`).
3. **Enrichment:** adds `data_quality` and `processed_timestamp`.
4. **Stores raw events** → `parking_events` table.
5. **Sliding-window aggregations** (1-min window, 2-min watermark): counts events,
   entries and exits per window → `parking_window_stats` table.

```python
parsed.withWatermark("event_time", "2 minutes") \
      .groupBy(col("lot_id"), window(col("event_time"), "1 minute")) \
      .agg(count(lit(1)).alias("event_count"),
           sum(when(col("event")=="entry",1).otherwise(0)).alias("entries"),
           sum(when(col("event")=="exit",1).otherwise(0)).alias("exits"))
```

In the local pipeline, the `LocalSparkStreaming` class + `SlidingWindowAggregator`
perform the same aggregations (count / entries / exits / avg_occupied /
vehicle_types) and expose them at the `/api/parking/windows` endpoint.

---

## 5. Data Storage in Cassandra

**Keyspace:** `smart_parking` (schema in `cassandra_schema.cql`, applied
automatically by `cassandra-init`).

```sql
CREATE TABLE parking_events (
    lot_id text, event_timestamp text, spot_id int, zone text, level text,
    event text, occupied text, vehicle_type text, occupancy_duration int,
    data_quality double, processed_timestamp text,
    PRIMARY KEY ((lot_id), event_timestamp, spot_id)
) WITH CLUSTERING ORDER BY (event_timestamp DESC, spot_id ASC);

CREATE TABLE parking_window_stats (
    lot_id text, window_start text, window_end text,
    event_count bigint, entries bigint, exits bigint,
    PRIMARY KEY ((lot_id), window_start)
) WITH CLUSTERING ORDER BY (window_start DESC);
```

- The **partition key** `lot_id` distributes data per parking lot.
- **Clustering order** by `event_timestamp DESC` allows fast reads of the most
  recent events (used by `/api/parking/events`).
- `occupied` is stored as `text` because it is boolean for entry/exit events and
  an integer count for status_update events.

---

## 6. Artificial Intelligence (AI/ML)

`parking_ml_service.py` trains real **scikit-learn** models on synthetic data that
models typical daily parking behavior (morning/evening peak load):

| Model | Algorithm | Task | Performance |
|---|---|---|---|
| Availability classifier | RandomForestClassifier | Predicts the future class (HIGH/MEDIUM/LOW/FULL) | ~86% accuracy |
| Demand predictor | RandomForestRegressor | Predicts occupancy 30 min ahead | MAE ~5% |
| Clusterer | KMeans | Clusters occupancy profiles | — |

- Models are trained automatically at startup and saved in `models/`.
- Predictions use the trained model; if the model is missing, the service falls
  back to rule-based logic.
- Features: `occupancy_rate`, `hour_of_day`, `day_of_week`, `is_weekend`,
  `recent_trend`. Feature importances are exposed at `/api/parking/ml-info`.
- Also includes **anomaly detection** (Z-score > 2.5σ).

---

## 7. Alarm System

`parking_alert_engine.py` monitors conditions and generates leveled alerts:

| Type | Condition | Level |
|---|---|---|
| LOT_FULL | occupancy ≥ 90% | CRITICAL |
| HIGH_OCCUPANCY | occupancy ≥ 75% | WARNING |
| ZONE_FULL | a zone ≥ 95% | WARNING |
| DEMAND_SPIKE | increase > 15% between windows | WARNING |
| ANOMALY_DETECTED | high Z-score | WARNING |

Alerts are shown in the dashboard **Alerts** tab and at `/api/parking/alerts`.

---

## 8. Performance Analysis & Optimization

`performance_monitor.py` measures real runtime metrics for each pipeline stage:
- **Throughput** (events/sec) for Kafka, Spark, Cassandra.
- **Latency** end-to-end and per-stage (avg / min / max / p95).
- **Counters** (messages, processed events, errors) and **data quality**.

Exposed at `/api/parking/performance` and in the dashboard **Performance** tab.

### 8.1 Benchmark results
The `benchmark.py` script loads the pipeline with a large event volume:

```
python benchmark.py --events 1500
```

Typical results (local pipeline, development machine):

| Metric | Value |
|---|---|
| Producer throughput (Kafka) | ~3,100 events/sec |
| End-to-end throughput (Spark→Cassandra) | ~170 events/sec |
| Cassandra write latency (avg) | ~4–6 ms |
| API latency (avg) | ~2 ms |
| Data quality | 100% |

### 8.2 Applied optimizations
- **Micro-batching** in Spark (2s interval) to balance latency vs. throughput.
- **Indexing** in Cassandra/SQLite on `(lot_id, event_timestamp)` for fast reads.
- **Disabling the Flask reloader** (`use_reloader=False`) to avoid double
  initialization of the pipeline.
- **History capping** (1000 samples) for controlled memory usage.

---

## 9. Visualization Interface

React dashboard (port 3000) with tabs:
- **Overview** — statistics, ML predictions, active alerts, recent events.
- **Zones** — occupancy per zone.
- **Trends** — historical occupancy chart.
- **Events** — event log from Cassandra.
- **Alerts** — active alerts.
- **Performance** — throughput, latency, sliding windows (chart).
- **System** — infrastructure status.

> 📸 _Insert dashboard screenshots here (Overview, Performance, Zones, Alerts)._

---

## 10. Conclusions and Recommendations

### 10.1 Achievements
- Full IoT pipeline: Sensors → Kafka → Spark → Cassandra → Visualization.
- All three advanced components: **AI/ML**, **Alarms**, **Performance**.
- Two execution modes (local for demo, Docker for production).
- Sliding-window aggregations in Spark Streaming.

### 10.2 Recommendations for improvement
- Train the ML models on real historical data (not only synthetic).
- Persist checkpoints and scale Spark to a cluster.
- Add authentication/authorization and HTTPS for the API.
- Integrate notifications (SMS/Email) for critical alerts.
- Support multiple parking lots (multi-lot) and real physical sensors.

---

## 11. How to Run

**Local (quick demo):**
```bash
pip install -r requirements.txt
npm install
python parking_api_endpoints.py     # Terminal 1
npm start                            # Terminal 2  → http://localhost:3000
```

**Docker (real Kafka/Spark/Cassandra):** see [DOCKER_PIPELINE.md](DOCKER_PIPELINE.md).
