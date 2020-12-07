import io
import json
import logging
import ntpath
import boto3
import pandas as pd
import sqlalchemy as sqlconnect


s3_client = boto3.client("s3")

class DBOps:
    """
    DB Connection Class To perform Data Write operations on the Database
    """
    ssl_args = {'ssl': {'ca_cert': 'rds-combined-ca-bundle.pem', 'sslmode': 'require', 'verify_ssl_cert': True}}

    def _getRdsPasswrdToken(self,dbConnParams: dict):
        """
        Generate the IAM based RDS Password authentication for the connection
        :param dbConnParams: DB Connection Params (DB Host Server and Credentials Info)
        :return: IAM Based Passwrord for RDS
        """
        global  data
        return boto3.client("rds").generate_db_auth_token(dbConnParams.get("host"), dbConnParams.get("port"),
                                                          dbConnParams.get("username"))

    def _createDBConnection(self, dbConnParams: dict):
        """
        Creating DB Connection object using SqlAchemy
        :param dbConnParams: DB Connection Params (DB Host Server and Credentials Info)
        :return: sqlalchemy DB Connection Object
        """
        logging.info("Creating DB Connection to {host}".format(host=dbConnParams.get("host")))
        print("Creating DB Connection to {host}".format(host=dbConnParams.get("host")))
        rds_credentials = {"user": dbConnParams.get("username"), "passwd": self._getRdsPasswrdToken(dbConnParams)}
        rds_credentials.update(self.ssl_args)
        return sqlconnect.create_engine(self._generateDbUrl(dbConnParams=dbConnParams),
                                        connect_args=rds_credentials).connect()

    def _generateDbUrl(self, dbConnParams: dict):
        """
        Generates the DB Connection URL in perspective to Python DB Connector
        :param dbConnParams: DB Connection Params (DB Host Server and Credentials Info)
        :return: DB Connection URL
        """
        if dbConnParams.get("dbType").lower() == "mysql":
            return "mysql+pymysql://@{host}/{service_db}".format(
                host=dbConnParams.get("host"),
                service_db=dbConnParams.get(
                    "service_db"))

    def writePandastoTable(self, df: pd.DataFrame, schema, tablename):
        """
        Writes the Pandas Dataframe to DB Table. Data write operation is only append. If table doesn't exists in the DB, it creates new table and load the data
        :param df: Source Data
        :param tablename: Target DB Table
        :param schema: Target DB Schema
        :return:
        """
        logging.info("Storing Dataframe data to " + schema + "." + tablename)
        print("Storing Dataframe data to " + schema + "." + tablename)
        df.to_sql(name=tablename, schema=schema, con=self._dbEngine, if_exists="append", index=False)

    def __init__(self, dbAwsParamid: dict):
        self._dbEngine = self._createDBConnection(dbAwsParamid)


def readS3FiletoPandas(bucketname: str, filekey: str) -> pd.DataFrame:
    """
    Reads the File from S3 Bucket and create pandas dataframe
    :param bucketname: S3 Bucket Name
    :param filekey: S3 Bucket Object Key
    :return: Dataframe with file data
    """
    logging.info("Reading File Data from s3://" + bucketname + "/" + filekey)
    print("Reading File Data from s3://" + bucketname + "/" + filekey)
    
    key_data = s3_client.get_object(Bucket=bucketname, Key=filekey)
    df = pd.read_csv(io.BytesIO(key_data['Body'].read()))
    return df

def getFileName(filePath):
    """
    Get the File Name from the path
    :param filePath: file name with path
    :return: return the filename
    """
    head, tail = ntpath.split(filePath)
    return tail or ntpath.basename(head)
    
def archiveS3Files(srcBucketname: str, srcFileKey: str, archiveBucketName: str, archivePath:str):
    """
    Archive the Source Files and delete the files from source location
    :param srcBucketname: Source Bucket Name
    :param srcFileKey: Source File Key
    :param archiveBucketName: Archive Bucket Name
    :param archivePath: Archive File Path
    :return:
    """
    logging.info("Archiving the Source file s3://{srcBucketname}/{srcFileKey} to s3://{archiveBucketName}/{archivePath}".format(srcBucketname=srcBucketname,srcFileKey=srcFileKey,archiveBucketName=archiveBucketName,archivePath=archivePath))
    print("Archiving the Source file s3://{srcBucketname}/{srcFileKey} to s3://{archiveBucketName}/{archivePath}".format(srcBucketname=srcBucketname,srcFileKey=srcFileKey,archiveBucketName=archiveBucketName,archivePath=archivePath))
    s3_client.copy(Bucket=archiveBucketName,Key=archivePath+getFileName(srcFileKey),CopySource={'Bucket':srcBucketname,'Key':srcFileKey})
    logging.info("Deleting the Source file s3://{srcBucketname}/{srcFileKey}".format(srcBucketname=srcBucketname,srcFileKey=srcFileKey))
    print("Deleting the Source file s3://{srcBucketname}/{srcFileKey}".format(srcBucketname=srcBucketname,srcFileKey=srcFileKey))
    s3_client.delete_object(Bucket=srcBucketname,Key=srcFileKey)
    

def getSSMParameter(param_name: str):
    """
    Fetches the Parameter info from the AWS Simple System Manager Paramenter Store
    :param param_name: SSM Parameter Store param name
    :return: dict object of param info
    """
    logging.info("Fetching " + param_name + " Param from Parameter Store")
    print("Fetching " + param_name + " Param from Parameter Store")
    return json.loads(boto3.client("ssm").get_parameter(Name=param_name).get("Parameter").get("Value"))
