import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, to_json, col, unbase64, base64, split, expr
from pyspark.sql.types import StructField, StructType, StringType, BooleanType, ArrayType, DateType, FloatType

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_HOST')

# TO-DO: create a StructType for the Kafka redis-server topic which has all changes made to Redis -
# before Spark 3.0.0, schema inference is not automatic

redis_schema = StructType([
    StructField('key', StringType()),
    StructField('existType', StringType()),
    StructField('ch', BooleanType()),
    StructField('incr', BooleanType()),
    StructField('zSetEntries', ArrayType(
        StructType([
            StructField('element', StringType()),
            StructField('score', FloatType())
        ])
    ))
])

# create a StructType for the Customer JSON that comes from Redis- before Spark 3.0.0, schema inference is not automatic
customer_json_schema = StructType([
    StructField('customerName', StringType()),
    StructField('email', StringType()),
    StructField('phone', StringType()),
    StructField('birthDay', DateType())
])

# create a StructType for the Kafka stedi-events topic which has the Customer Risk JSON that comes from Redis
# - before Spark 3.0.0, schema inference is not automatic

stedi_event = StructType([
    StructField('customer', StructType()),
    StructField('score', FloatType()),
    StructField('riskDate', DateType())
])


# create a spark application object
spark = SparkSession\
    .builder\
    .appName("customer-join")\
    .getOrCreate()

# set the spark log level to WARN
spark.sparkContext.setLogLevel('WARN')

# using the spark application object, read a streaming dataframe from the Kafka topic redis-server as the source
# Be sure to specify the option that reads all the events from the topic including those
# that were published before you started the spark stream
redis_data_df = spark.readStream \
    .format('kafka') \
    .option('kafka.bootstrap.servers', KAFKA_BOOTSTRAP_SERVERS) \
    .option('subscribe', 'redis-server') \
    .option('startingOffsets', 'earliest') \
    .load()


# cast the value column in the streaming dataframe as a STRING

redis_data_df = redis_data_df \
    .withColumn('value', col('value').cast(StringType()))

# parse the single column "value" with a json object in it, like this:
# +------------+
# | value      |
# +------------+
# |{"key":"Q3..|
# +------------+
#
# with this JSON format: {"key":"Q3VzdG9tZXI=",
# "existType":"NONE",
# "Ch":false,
# "Incr":false,
# "zSetEntries":[{
# "element":"eyJjdXN0b21lck5hbWUiOiJTYW0gVGVzdCIsImVtYWlsIjoic2FtLnRlc3RAdGVzdC5jb20iLCJwaG9uZSI6IjgwMTU1NTEyMTIiLCJiaXJ0aERheSI6IjIwMDEtMDEtMDMifQ==",
# "Score":0.0
# }],
# "zsetEntries":[{
# "element":"eyJjdXN0b21lck5hbWUiOiJTYW0gVGVzdCIsImVtYWlsIjoic2FtLnRlc3RAdGVzdC5jb20iLCJwaG9uZSI6IjgwMTU1NTEyMTIiLCJiaXJ0aERheSI6IjIwMDEtMDEtMDMifQ==",
# "score":0.0
# }]
# }
#
# (Note: The Redis Source for Kafka has redundant fields zSetEntries and zsetentries, only one should be parsed)
#
# and create separated fields like this:
# +------------+-----+-----------+------------+---------+-----+-----+-----------------+
# |         key|value|expiredType|expiredValue|existType|   ch| incr|      zSetEntries|
# +------------+-----+-----------+------------+---------+-----+-----+-----------------+
# |U29ydGVkU2V0| null|       null|        null|     NONE|false|false|[[dGVzdDI=, 0.0]]|
# +------------+-----+-----------+------------+---------+-----+-----+-----------------+
#
# storing them in a temporary view called RedisSortedSet

redis_data_df \
    .withColumn('value', from_json(col('value'), redis_schema)) \
    .select(col('value.*')) \
    .createOrReplaceTempView('RedisSortedSet')

# execute a sql statement against a temporary view, which statement takes
# the element field from the 0th element in the array of structs and create a column called encodedCustomer
# the reason we do it this way is that the syntax available select against a view is different than a dataframe,
# and it makes it easy to select the nth element of an array in a sql column

customers_df = spark.sql('SELECT zSetEntries[0].element as encodedCustomer FROM RedisSortedSet')

# take the encodedCustomer column which is base64 encoded at first like this:
# +--------------------+
# |            customer|
# +--------------------+
# |[7B 22 73 74 61 7...|
# +--------------------+

# and convert it to clear json like this:
# +--------------------+
# |            customer|
# +--------------------+
# |{"customerName":"...|
#+--------------------+
#
# with this JSON format: {"customerName":"Sam Test","email":"sam.test@test.com","phone":"8015551212","birthDay":"2001-01-03"}

customers_json = customers_df \
    .withColumn('customer', unbase64(col('encodedCustomer')).cast(StringType()))

# parse the JSON in the Customer record and store in a temporary view called CustomerRecords
customers_json \
    .withColumn('customer', from_json(col('customer'), customer_json_schema)) \
    .select(col('customer.*')) \
    .createOrReplaceTempView('CustomerRecords')

# JSON parsing will set non-existent fields to null, so let's select just the fields we want,
# where they are not null as a new dataframe called emailAndBirthDayStreamingDF
emailAndBirthDayStreamingDF = spark.sql('SELECT * FROM CustomerRecords') \
    .dropna(how='any') \
    .select(col('email'),
            col('birthDay'))

# from the emailAndBirthDayStreamingDF dataframe select the email and the birth year (using the split function)
# Split the birth year as a separate field from the birthday
# Select only the birth year and email fields as a new streaming data frame called emailAndBirthYearStreamingDF

emailAndBirthYearStreamingDF = emailAndBirthDayStreamingDF \
    .withColumn('birthYear', split(col('birthDay').cast(StringType()), '-').getItem(0))



# sink the emailAndBirthYearStreamingDF dataframe to the console in append mode
#
# The output should look like this:
# +--------------------+-----
# | email         |birthYear|
# +--------------------+-----
# |Gail.Spencer@test...|1963|
# |Craig.Lincoln@tes...|1962|
# |  Edward.Wu@test.com|1961|
# |Santosh.Phillips@...|1960|
# |Sarah.Lincoln@tes...|1959|
# |Sean.Howard@test.com|1958|
# |Sarah.Clark@test.com|1957|
# +--------------------+-----

# Run the python script by running the command from the terminal:
# /home/workspace/submit-redis-kafka-streaming.sh
# Verify the data looks correct

emailAndBirthYearStreamingDF \
    .writeStream \
    .outputMode('append') \
    .format('console') \
    .start() \
    .awaitTermination()
