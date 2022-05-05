import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, unbase64, base64, split
from pyspark.sql.types import StructField, StructType, StringType, BooleanType, ArrayType, DateType, FloatType

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_HOST')

event_schema = StructType([
    StructField('customer', StringType()),
    StructField('score', FloatType()),
    StructField('riskDate', DateType())
])

spark = SparkSession\
    .builder\
    .appName("kafka_event_stream_to_console")\
    .getOrCreate()

spark.sparkContext.setLogLevel('WARN')

# using the spark application object, read a streaming dataframe from the Kafka topic stedi-events as the source
# Be sure to specify the option that reads all the events from the topic including those
# that were published before you started the spark stream

# using the spark application object, read a streaming dataframe from the Kafka topic redis-server as the source
events_df = spark.readStream \
    .format('kafka') \
    .option('kafka.bootstrap.servers', KAFKA_BOOTSTRAP_SERVERS) \
    .option('subscribe', 'stedi-events') \
    .option('startingOffsets', 'earliest') \
    .load()

# cast the value column in the streaming dataframe as a STRING
events_df = events_df \
    .withColumn('value', col('value').cast(StringType()))

# TO-DO: parse the JSON from the single column "value" with a json object in it, like this:
# +------------+
# | value      |
# +------------+
# |{"custom"...|
# +------------+
#
# and create separated fields like this:
# +------------+-----+-----------+
# |    customer|score| riskDate  |
# +------------+-----+-----------+
# |"sam@tes"...| -1.4| 2020-09...|
# +------------+-----+-----------+
#
# storing them in a temporary view called CustomerRisk

events_df \
    .withColumn('value', from_json(col('value'), event_schema)) \
    .select(col('value.*')) \
    .createOrReplaceTempView('CustomerRisk')

# execute a sql statement against a temporary view,
# selecting the customer and the score from the temporary view, creating a dataframe called customerRiskStreamingDF

customerRiskStreamingDF = spark.sql('SELECT customer, score FROM CustomerRisk customer_risk')

# sink the customerRiskStreamingDF dataframe to the console in append mode
#
# It should output like this:
#
# +--------------------+-----
# |customer           |score|
# +--------------------+-----+
# |Spencer.Davis@tes...| 8.0|
# +--------------------+-----
# Run the python script by running the command from the terminal:
# /home/workspace/submit-event-kafka-streaming.sh
# Verify the data looks correct

customerRiskStreamingDF \
    .writeStream \
    .outputMode('append') \
    .format('console') \
    .start() \
    .awaitTermination()