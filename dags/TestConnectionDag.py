from datetime import datetime, timedelta

from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.operators.mysql_operator import MySqlOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook

import pandas as pd
import boto3


S3_CONN = "s3_conn"


default_args = {

    "owner": "airflow",
    'retry': 1,
    'retry_delay': timedelta(minutes=5),
    # 'start_date': datetime(2024, 6, 5),
    'start_date': days_ago(0),
    'catchup': False

}


def testS3Hook():

    bucketName = 'bucket0'
    s3_hook = S3Hook(aws_conn_id=S3_CONN)
    print(s3_hook)
    paths = s3_hook.list_keys(bucket_name=bucketName)
    print(paths)


def botoTest():
    s3 = S3Hook(aws_conn_id=S3_CONN)
    print(s3)

    exist1 = s3.check_for_bucket('bucket0')
    print(exist1)
    exist2 = s3.check_for_key('pkm1.csv', 'bucket0')
    print(f"bucket:{exist1}, file exist:{exist2}")


with DAG(
    default_args=default_args,
    dag_id="dag_testConnection_v1",
    schedule_interval='@daily'
) as dag:

    t0 = DummyOperator(
        task_id='dummy',
    )

    t1 = PythonOperator(
        task_id='test_first_connection',
        python_callable=lambda: print("testing task1")
    )

    t2 = MySqlOperator(
        task_id='test_mysql_connection',
        mysql_conn_id="mysql_conn",
        sql="select * from dest.pokedex"
    )

    t3 = PythonOperator(
        task_id="test_boto",
        python_callable=botoTest)

    t4 = PythonOperator(
        task_id="test_s3_hook",
        python_callable=testS3Hook)

# test airflow connection and python operator
t0 >> t1

# test connection with mysql
t2

# test connection with minio s3
t3 >> t4
