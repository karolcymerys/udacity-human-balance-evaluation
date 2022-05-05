#!/bin/bash
sudo docker exec -it  \
  udacity-human-balance-evaluation-spark-master-1 \
   /opt/bitnami/spark/bin/spark-submit \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.2.1 \
    /home/workspace/pyspark_kafka_event_stream_to_console/sparkpyeventskafkastreamtoconsole.py | tee ../spark/logs/eventstream.log

