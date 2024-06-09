from airflow.hooks.base import BaseHook
from airflow.hooks.mysql_hook import MySqlHook
from airflow.models.baseoperator import BaseOperator


class MySqlOperator76(BaseOperator):

    def __init__(
        self,
        #sql query statement
        sql=None,
        mysql_conn_id='mysql_default',
        #can be useful to retrieve s3 objectst
        aws_conn_id='aws_default',
        tbl_name=None,
        lisObj=None,
        *args,
        **kwargs,
    ) -> None:
        self.mysql_conn_id = mysql_conn_id
        self.aws_conn_id = aws_conn_id
        self.tbl_name = tbl_name
        self.sql = sql
        self.lisObj = lisObj
        super().__init__(*args, **kwargs)

    def execute(self, context):
        
        print("using custom operator...")

        mysql_hook = MySqlHook(self.mysql_conn_id)

        print(mysql_hook)

        conn = mysql_hook.get_conn()

        cursor = conn.cursor()

        cursor.execute(self.sql)

        rows = cursor.fetchall()

        for r in rows:
            print(r)


        cursor.close()
        conn.close()


