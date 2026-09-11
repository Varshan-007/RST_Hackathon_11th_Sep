import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Neo4j Settings
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "csvgraphdb")
    neo4j_database: str = os.getenv("NEO4J_DATABASE", "neo4j")

    # Kafka Settings
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    kafka_topic: str = os.getenv("KAFKA_TOPIC", "csv-rows")
    kafka_group_id: str = os.getenv("KAFKA_GROUP_ID", "neo4j-loader-group")

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
