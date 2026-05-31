# 🐳 Real Apache Kafka → Spark → Cassandra Pipeline (Docker)

This is the **production** pipeline using real Apache Kafka, Apache Spark
Structured Streaming and Apache Cassandra. (For development/demos without
Docker, the in-process `local_pipeline.py` simulates the same flow — see the
main [README](README.md).)

```
Sensor Simulator (host)          Docker network
  kafka_simulator_runner.py  →  Kafka  →  Spark Streaming  →  Cassandra
                              (parking-events)   (windowing)   (smart_parking)
```

## Prerequisites
- Docker Desktop (with `docker compose`)
- Python 3.8+ on the host (for the producer): `pip install -r requirements.txt`

## 1. Start the infrastructure

```bash
docker compose up -d
```

This starts:
| Service | Purpose | Port |
|---|---|---|
| `zookeeper` | Kafka coordination | 2181 |
| `kafka` | Message broker | 9092 (host) / 29092 (internal) |
| `kafka-init` | Creates the `parking-events` topic | — |
| `cassandra` | Time-series database | 9042 |
| `cassandra-init` | Applies `cassandra_schema.cql` (keyspace + tables) | — |
| `spark` | Spark runtime (idle until you submit the job) | — |

Wait until Kafka and Cassandra are healthy (~60–90s on first run):

```bash
docker compose ps
```

`kafka-init` and `cassandra-init` should show `Exited (0)` once they've created
the topic and schema.

## 2. Submit the Spark Streaming job

```bash
docker exec -it smartparking-spark /opt/spark/bin/spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.6,com.datastax.spark:spark-cassandra-connector_2.12:3.5.1 \
  --conf spark.cassandra.connection.host=cassandra \
  /app/spark_streaming_job.py
```

(First run downloads the Kafka + Cassandra connector jars; leave it running.)

## 3. Start the sensor simulator (host → Kafka)

In a new terminal:

```bash
python kafka_simulator_runner.py
```

This streams entry/exit + status_update events to `localhost:9092`.

## 4. Verify data is flowing

```bash
# Raw processed events
docker exec -it smartparking-cassandra cqlsh -e \
  "SELECT * FROM smart_parking.parking_events LIMIT 10;"

# Windowed aggregations
docker exec -it smartparking-cassandra cqlsh -e \
  "SELECT * FROM smart_parking.parking_window_stats LIMIT 10;"
```

## 5. Tear down

```bash
docker compose down          # stop containers
docker compose down -v       # also remove volumes/data
```

## Troubleshooting
- **Kafka not healthy**: give it more time on first boot; check `docker compose logs kafka`.
- **Spark can't reach Kafka/Cassandra**: the job uses the internal hostnames
  `kafka:29092` and `cassandra:9042` — only valid *inside* the Docker network
  (i.e. run via `docker exec`, not from the host).
- **Producer connection refused**: ensure `docker compose ps` shows kafka `healthy`
  and that you're connecting to `localhost:9092` from the host.
