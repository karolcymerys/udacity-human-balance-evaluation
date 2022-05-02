#!/bin/bash
sudo docker exec -it  \
  udacity-human-balance-evaluation-spark-master-1 \
   /opt/bitnami/spark/bin/spark-submit \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.0.0 \
    /home/workspace/pyspark_kafka_join/sparkpykafkajoin.py | tee ../spark/logs/kafkajoin.log
