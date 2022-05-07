# Udacity evaluate human balance

This is final project for lesson Streaming API Development and Documentation in Udacity Data Streaming Nanodegree. 
The main goal of this project is to prepare streaming data pipeline based on Kafka and Spark Streaming.
Events are produced by business application called STEDI. Application is simulating performing small exercise by seniors to assess balance for seniors.
Data collected by applications are stored in Redis and propagated to Kafka topic. 
Next data are consumed by Spark and processed. 
Results are propagated to next Kafka topic.
Finally, application STEDI is consuming this topic to present a data in form of graph.

## Architecture
![Architecture](images/architecture.png?raw=true "Architecture")
## Proof of working
![Fetching data Staring spark cluster initialization](images/docker-compose.png?raw=true "Staring spark cluster initialization")
![Graph1](images/graph_1.png?raw=true "Graph 1")
![Graph2](images/graph_2.png?raw=true "Graph 2")

## Start application
### Requirements
- docker
- docker-compose

Run `docker-compose up`

In order to run spark applications:
- go to `pyspark_kafka_event_stream_to_console` and run `./submit.sh`
- go to `pyspark_kafka_join` and run `./submit.sh`
- go to `pyspark_kafka_redis_stream_to_console` and run `./submit.sh`
