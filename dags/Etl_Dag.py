
# https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/_api/airflow/providers/amazon/aws/hooks/s3/index.html#module-airflow.providers.amazon.aws.hooks.s3

from datetime import datetime, timedelta
from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.python import PythonOperator
# from airflow.operators.mysql_operator import MySqlOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.hooks.mysql_hook import MySqlHook

from custom_operators.mySql_operator76 import MySqlOperator76
from io import StringIO

import csv
import pandas as pd
import os
import tempfile
import logging

# import utils.constants as c
# import utils.helpers as helpers


from utils.constants import S3_CONN, MY_SQL_CONN, SOURCE_BUCKET, POKEDEX_BUCKET, POKEFIELDNAMES
import utils.helpers as helpers

s3_conn = S3_CONN
mySql_conn = MY_SQL_CONN
sourceBucket = SOURCE_BUCKET
pokeBucket = POKEDEX_BUCKET


default_args = {

    "owner": "airflow",
    'retry': 1,
    'retry_delay': timedelta(minutes=5),
    # 'start_date': datetime(2024, 6, 5),
    'start_date': days_ago(0),
    'catchup': False

}


def ingest():

    s3_hook = S3Hook(aws_conn_id=s3_conn)
    found = s3_hook.check_for_bucket(sourceBucket)

    if not found:
        # create bucket
        print(f"bucket {sourceBucket} created !")
        s3_hook.create_bucket(sourceBucket)

    else:
        print(f"bucket {sourceBucket} already exists !")

    # list of fileName str  in bucket /w prefix
    ls_keys = s3_hook.list_keys(sourceBucket)

    if not ls_keys:
        return

    # #get boto3 object
    s3_Obj = s3_hook.get_key(ls_keys[0], sourceBucket)

    # get content
    res = s3_Obj.get()

    content1 = res['Body']

    # for reading the content only
    content2 = res['Body'].read().decode('utf-8')
    print(content2)

    # read into dataframe
    df1 = pd.read_csv(StringIO(content2))
    print(df1)


def ingest2(ti, _currDate=None):

    s3_hook = S3Hook(aws_conn_id=s3_conn)
    found = s3_hook.check_for_bucket(pokeBucket)

    if not found:
        # print(f"bucket {pokeBucket} created !")
        # s3_hook.create_bucket(pokeBucket)

        print(f'Bukcket {pokeBucket} not found')
        ti.xcom_push(key='flagContinue', value=False)
        return

    # check for prefix

    currDate = _currDate if _currDate is not None else helpers.getCurrentDate()
    print(currDate + ' here')

    # targetPrefix = f"{currDate}/landing/*.csv"
    targetPrefix = f"{currDate}/landing/"
    print(targetPrefix)

    prefixExist = s3_hook.check_for_prefix(targetPrefix, "/", pokeBucket)

    # list all file in thr bucket with that prefix
    ls_files = s3_hook.list_keys(pokeBucket, targetPrefix, '/')
    print(ls_files)

    if (ls_files):

        # remove all non-csv files
        # error prone using this method
        # csvFiles = list(filter(lambda x: x.split('.')[1] == 'csv', ls_files))

        csvFiles = list(filter(lambda x: x.endswith('.csv'), ls_files))
        print(csvFiles)

    else:
        print('not files detected')
        print("exiting ...")
        ti.xcom_push(key='flagContinue', value=False)

        return

    if not csvFiles:
        print('no csv files detected')
        print("exiting ...")
        ti.xcom_push(key='flagContinue', value=False)
        return

    # to contain list of object
    resLis = []

    # combine as single file for archive
    for f in csvFiles:
        try:
            print(f"working on file{f}")
            s3_Obj = s3_hook.get_key(f, pokeBucket)
            res = s3_Obj.get()

            content: str = res['Body'].read().decode('utf-8')
            # b'id,name,type1,type2,hp,attack,defense,speed\r\n1,bulbasaur,grass,poision,45,49,49,45\r\n4,charmander,fire,,39,52,42,65\r\n7,squirtle,water,,44,48,65,43\r\n'
            # print(content)

            # split by the newline \r\n
            # omit the header
            contentSplit = content.splitlines()
            contentSplit = contentSplit[1:]
            # print(contentSplit)

            # transform into object and add to res Lis

            for s1 in contentSplit:

                # s1 is string content or stats for 1 pokemon
                # we split into list to get the stats for that pokemon
                temp: list = s1.split(',')

                pokemon = {
                    "id": temp[0],
                    "name": temp[1],
                    "type1": temp[2],
                    "type2": temp[3],
                    "hp": temp[4],
                    "attack": temp[5],
                    "defense": temp[6],
                    "speed": temp[7]
                }

                resLis.append(pokemon)

        except Exception as e:
            print('An exception occurred')
            print(e)
            continue

    # print(resLis)

    # convert into 1 single csv file
    fileDict = writeToCsv(resLis)
    print(fileDict)

    # push to xcom about the information
    ti.xcom_push(key='fileDict', value=fileDict)
    ti.xcom_push(key='test', value='one')
    ti.xcom_push(key='flagContinue', value=True)

    # upsert each file content to db
    for x in csvFiles:
        pass


def writeToCsv(pokemonLis: list):

    ts = helpers.getCurrentTimeStamp()

    filename = f"/local/{ts}_output.csv"

    dagPath = os.path.dirname(__file__)
    csvDir = f"/{dagPath}/../local"
    # csvDir = f"/{dagPath}/local"
    filename = f"{csvDir}/{ts}_combined.csv"

    print(filename)

    with open(filename, 'w+',) as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=POKEFIELDNAMES)

        # writing headers (field names)
        writer.writeheader()

        # writing data rows
        writer.writerows(pokemonLis)

    return {"timeStamp": ts, "filePath": filename}


def uploadToCsv(_location, ti):

    # dummy object
    # {'timeStamp': '20240607121326', 'filePath': '//opt/***/dags/local/20240607121326_output.csv'}

    proceed = ti.xcom_pull(key="flagContinue", task_ids="ingest_test1")

    if not proceed:
        print(f"unable to proced due to xcom flag: {proceed}")
        return

    print(f'prepare to upload csv file at {_location} folder')
    print(_location)

    # xTest = ti.xcom_pull(key="test", task_ids="ingest_test1")
    # print(xTest)

    fDict = ti.xcom_pull(key="fileDict", task_ids="ingest_test1")
    print(fDict)

    s3_hook = S3Hook(aws_conn_id=s3_conn)
    found = s3_hook.check_for_bucket(pokeBucket)

    if not found:
        print(
            f"bucket {pokeBucket} dont exist. pls create bucket before proceeding!")
        return

    # get date from fileName
    datePrefix = fDict['timeStamp'][0:8]
    ts = fDict['timeStamp']

    # localfilePath to be upload
    localFp = fDict['filePath']

    print(ts)
    print(datePrefix)

    # upload to 20240607/transform/1233_combined.csv
    targetKey = f"{datePrefix}/{_location}/{ts}_combined.csv"
    print(targetKey)

    # check file exist in local
    print(localFp)

    localFileExist = os.path.isfile(localFp)
    print(f"file exist ???:{localFileExist}")

    if localFileExist:
        print("uploading file to s3 now...")
        s3_hook.load_file(localFp, targetKey, pokeBucket)
        print("file uploded")

    else:
        print("file not found.Unable to upload ")


def uploadNextDay():

    s3_hook = S3Hook(aws_conn_id=s3_conn)

    # create tmr prefix
    tmrStr = helpers.getNextDayDate()
    tmr_targetPrefix = f"{tmrStr}/landing/"
    tmr_targetPrefix2 = f"{tmrStr}/transform/"
    # print(tmr_targetPrefix)

    print("creating nextDayFolder...")

    tmrPrefixExist = s3_hook.check_for_prefix(
        tmr_targetPrefix, "/", pokeBucket)

    if tmrPrefixExist:

        print("landing prefix for next day already exist")

    else:
        s3_hook.load_string('', tmr_targetPrefix, pokeBucket)
        print("landing prefix for next day created")

    tmrPrefixExist2 = s3_hook.check_for_prefix(
        tmr_targetPrefix2, "/", pokeBucket)

    if tmrPrefixExist2:

        print("transfrom prefix for next day already exist")

    else:
        s3_hook.load_string('', tmr_targetPrefix2, pokeBucket)
        print("transform prefix for next day created")


def uploadDay(_currDate=None, _bucketName=None):

    print(f"from args: {_currDate}")

    if _currDate is None:
        _currDate = helpers.getCurrentDate()

    if _bucketName is None:
        _bucketName = pokeBucket

    s3_hook = S3Hook(aws_conn_id=s3_conn)
    foundBucket = s3_hook.check_for_bucket(_bucketName)

    targetPrefix = f"{_currDate}/landing/"
    targetPrefix2 = f"{_currDate}/transform/"
    # print(tmr_targetPrefix)

    prefixExist = s3_hook.check_for_prefix(targetPrefix, "/", pokeBucket)

    if prefixExist:

        print(f"landing prefix for {_currDate} already exist")

    else:
        s3_hook.load_string('', targetPrefix, pokeBucket)
        print(f"landing prefix for next day created")

    prefixExist2 = s3_hook.check_for_prefix(targetPrefix2, "/", pokeBucket)

    if prefixExist2:

        print(f"transform prefix for {_currDate} already exist")

    else:
        s3_hook.load_string('', targetPrefix2, pokeBucket)
        print(f"transform prefix for {_currDate} created")


def transformUpload():

    s3_hook = S3Hook(aws_conn_id=s3_conn)
    foundBucket = s3_hook.check_for_bucket(pokeBucket)

    currDate = helpers.getCurrentDate()
    transformPrefix = f"{currDate}/transform/"
    transformPrefixCsv = f"{currDate}/transform/*.csv"

    transformPrefixExist = s3_hook.check_for_prefix(
        transformPrefix, "/", pokeBucket)

    if not foundBucket or not transformPrefixExist:
        print("bucket or prefix not found")
        print("exiting...")

    lis_keys = s3_hook.list_keys(
        pokeBucket, transformPrefixCsv, '/', apply_wildcard=True)
    lis_s3obj = [
        {"key": x, **s3_hook.get_key(x, pokeBucket).get()} for x in lis_keys]

    # print(lis_s3obj)

    if not lis_s3obj:
        print("no files detected")
        print("exiting...")
        return

    # sortedLis1 = [obj['key']for obj in sorted(lis_s3obj, key=lambda x: x['LastModified'])]
    sortedList=[ obj['key'] for obj in sorted(lis_s3obj,key=lambda x:x['LastModified'], reverse=True)]

    print(sortedList)
    # get the latest file in the transform file
    latestFileKey = sortedList[0]

    print(f"latest file in tranfrom folder: {latestFileKey}")

    # work with dataframe
    tempDf = pd.DataFrame()

    # download from s3 bucket
    with tempfile.TemporaryDirectory() as temp_dir:

        # _tmpFilePath = os.path.join(temp_dir,'temp.csv')
        dl_fileName = s3_hook.download_file(
            latestFileKey, pokeBucket, temp_dir)
        # print(dl_fileName)
        tempDf = pd.read_csv(dl_fileName)
        # print(tempDf)

    # do the processing here ...
    # cleaning >> transforming

    s3_hook = S3Hook(aws_conn_id=s3_conn)
    found = s3_hook.check_for_bucket(pokeBucket)

    # upload new file to output folder in s3
    with tempfile.NamedTemporaryFile() as f:

        tempDf.to_csv(f, encoding='utf-8', index=False)
        # upload to csv
        print(latestFileKey)
        datePrefix = latestFileKey.split('/')[0]

        targetKey = f"{datePrefix}/output/{datePrefix}_finalRes.csv"
        print(targetKey)

        print(f.name)

        s3_hook.load_file(f.name, targetKey, pokeBucket, True)


# pass in date to process
def upsertDb(_currDate=None, _bucketName=None):

    print(f"from args: {_currDate}")

    if _currDate is None:
        _currDate = helpers.getCurrentDate()

    if _bucketName is None:
        _bucketName = pokeBucket

    # print(_currDate)
    # print(_bucketName)

    # check bucket and prefix exist
    s3_hook = S3Hook(aws_conn_id=s3_conn)
    foundBucket = s3_hook.check_for_bucket(_bucketName)

    targetPrefix = f"{_currDate}/output/"

    outputKey = f"{_currDate}/output/{_currDate}_finalRes.csv"

    outputPrefixExist = s3_hook.check_for_prefix(
        targetPrefix, "/", _bucketName)

    if not foundBucket or not outputPrefixExist:
        print("bucket or prefix not found")
        print("exiting...")

    # retreive the document and read the cotents
    print(outputKey)

    targetKeyExist = s3_hook.check_for_key(outputKey, _bucketName)

    if not targetKeyExist:
        print("file/key in bucket dont exist")
        return

    # read contents ??
    content = s3_hook.read_key(outputKey, _bucketName)
    print(content)
    # print(type(content))

    # remove header form list, split by newlines
    lis = content.splitlines()[1:]
    # print(lis)

    # list of list for easy inserting
    dbList = list(map(lambda x: x.split(','), lis))
    print(dbList)

    # prepare for reading using mysql

    logging.info("preparing to upload data to db")

    # print(mySql_conn)

    mysql_hook = MySqlHook(mySql_conn)

    conn = mysql_hook.get_conn()

    cursor = conn.cursor()

    # values(%s,%s,%s,%s,%s,%s,%s,%s)
    # values("%s","%s","%s","%s","%s","%s","%s","%s")

    insertQuery = '''insert into dest.pokedex(Pokedex_id,Name,Type1,Type2,Hp,Attack,Defense,Speed)
                values(%s,%s,%s,%s,%s,%s,%s,%s)
                as new
                on duplicate key update
                    Type1= new.Type1,
                    Type2= new.Type2,
                    Hp= new.Hp,
                    Attack=new.Attack,
                    Defense=new.Defense,
                    Speed= new.Speed;
    '''

    for row in dbList:

        try:
            logging.info(f"working on row{row[0], row[1]}")
            cursor.execute(insertQuery, (int(row[0]), str(row[1]), str(row[2]), str(
                row[3]), int(row[4]), int(row[5]), int(row[6]), int(row[7])))
            conn.commit()

        except Exception as e:
            print('An exception occurred')
            print(e)

        # print(( int(row[0]),row[1],row[2],row[3],int(row[4]),int(row[5]),int(row[6]),int(row[7])))

    cursor.close()
    conn.close()

    pass


with DAG(
    default_args=default_args,
    dag_id="etl_t1",
    schedule_interval='@daily'
) as dag:

    # ingest + compile csv into 1
    t1 = PythonOperator(
        task_id='ingest_test1',
        python_callable=ingest2,
        op_kwargs={'_currDate': None}

    )

    # upload csv to different location
    t2 = PythonOperator(
        task_id='upload_test1',
        python_callable=uploadToCsv,
        op_kwargs={'_location': 'transform'}

    )

    # prepare for next day bucket structure
    t3 = PythonOperator(
        task_id='upload_nextDay1',
        python_callable=uploadNextDay,
    )

    # prepare for day x bucket structure
    t4 = PythonOperator(
        task_id='upload_day',
        python_callable=uploadDay,
        # op_kwargs={'currDate': '20240607' , '_bucketName': 'ash'}
    )

    # transform + upload
    t5 = PythonOperator(
        task_id='transformTest',
        python_callable=transformUpload

    )

    # download csv from s3  and  upload to db
    t6 = PythonOperator(
        task_id='upsertDbTest',
        python_callable=upsertDb,
        # op_kwargs={'currDate': '20240607' , '_bucketName': 'ash'}

    )

    # using custom operator to do query
    # for testing feature
    t8 = MySqlOperator76(
        task_id='customOperator_test',
        sql="select * from dest.pokedex",
        mysql_conn_id=mySql_conn,
        aws_conn_id=s3_conn,
        tbl_name='pokedex'
    )


# prepare the bucket folder structure
t4>>t3

# ingest files and complie to 1 file  >> tranform buckeet
t1 >> t2

# transfrom file and upload to output >> insert output file contenet into database
t5 >> t6
