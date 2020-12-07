import logging

from Ops import DBOps
from Ops import readS3FiletoPandas
from Ops import getSSMParameter
from Ops import archiveS3Files

def lambda_handler(event, context):
    for index in range(len(event)):

        bucket = event['Records'][index]['s3']['bucket']['name']
        fileKey = event['Records'][index]['s3']['object']['key']
        # Connection Params Structure
        # {
        #     "dbType": "DB Type",
        #     "host": "DB Host Address",
        #     "username": "DB User Name",
        #     "port": "DB Port",
        #     "service_db": "Database Connection service Name",
        #     "mysql_schema": "Mysql Schema Name",
        #     "mysql_tbl": "Mysql table name",
        #     "archiveBucket": "Archive Bucket Name",
        #     "archivePath": "Archive Path"
        # }
        conn_params = getSSMParameter("RDS_Mysql_Secrects")
        csv_data_df = readS3FiletoPandas(bucket, fileKey)
        if len(csv_data_df) > 0:
            sqlEngine = DBOps(conn_params)
            sqlEngine.writePandastoTable(csv_data_df, schema=conn_params.get("mysql_schema"), tablename=conn_params.get("mysql_tbl"))
        else:
            logging.error("Source File is Empty")
            print("Source File is Emtpy")
            raise Exception("Source File is Empty")
        archiveS3Files(srcBucketname=bucket, srcFileKey=fileKey, archiveBucketName=conn_params.get("archiveBucket"), archivePath=conn_params.get("archivePath"))
