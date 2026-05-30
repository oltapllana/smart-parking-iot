import json
from kafka import KafkaProducer


class ParkingKafkaProducer:
    def __init__(self, bootstrap_servers="localhost:9092", topic="parking-events"):
        self.topic = topic
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            key_serializer=lambda key: str(key).encode("utf-8") if key is not None else None,
        )

    def send_event(self, event):
        self.producer.send(
            self.topic,
            key=event.get("spot_id"),
            value=event
        )
        self.producer.flush()