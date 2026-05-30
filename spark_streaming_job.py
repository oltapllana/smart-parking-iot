from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, BooleanType


spark = SparkSession.builder \
    .appName("SmartParkingSparkStreaming") \
    .config("spark.cassandra.connection.host", "smartparking-cassandra") \
    .config("spark.cassandra.connection.port", "9042") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

schema = StructType([
    StructField("lot_id", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("spot_id", IntegerType(), True),
    StructField("zone", StringType(), True),
    StructField("level", StringType(), True),
    StructField("event", StringType(), True),
    StructField("occupied", BooleanType(), True),
    StructField("vehicle_type", StringType(), True),
    StructField("occupancy_duration", IntegerType(), True),
])

raw_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "smartparking-kafka:29092") \
    .option("subscribe", "parking-events") \
    .option("startingOffsets", "latest") \
    .load()

parsed_stream = raw_stream.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")

cassandra_stream = parsed_stream \
    .withColumnRenamed("timestamp", "event_timestamp")


def write_to_cassandra(batch_df, batch_id):
    if batch_df.count() > 0:
        batch_df.write \
            .format("org.apache.spark.sql.cassandra") \
            .mode("append") \
            .options(table="parking_events", keyspace="smart_parking") \
            .save()

        print(f"✅ Batch {batch_id} saved to Cassandra")


query = cassandra_stream.writeStream \
    .foreachBatch(write_to_cassandra) \
    .outputMode("append") \
    .start()

query.awaitTermination()