Read Me

## Setup Lambda Function for S3 Files to Mysql Database Load

To illustrate the example, we need below aws resources created before creating the function, make sure you have proper permissions to create AWS resources,

1.  Create VPC network or use the default VPC in the region. (Will be using the Default VPC in the Region)
2.  Create VPC endpoints for SSM and S3 and attach the VPC created above or VPC your are using with subnets and route table.
3.  Create MySQL RDS database with IAM DB Authentication.
4.  Create role with specific policy to access the S3, IAM Authentication for RDS and lambda execution role.
5.  Create a source bucket for CSV files.
6.  Create Parameter in SSM Parameter Store.
7.  Creating the lambda layer for python library.

## Create VPC Endpoints

1.  Create VPC Endpoints to access the AWS services in private which are out of the VPC network,
    
    ```
     aws ec2 modify-vpc-attribute --enable-dns-hostnames  --vpc-id <VPC-ID> 
     aws ec2 modify-vpc-attribute --enable-dns-support  --vpc-id <VPC-ID> 
     aws ec2 create-vpc-endpoint --vpc-id <VPC-ID> --service-name com.amazonaws.<aws-region>.ssm  --vpc-endpoint-type Interface --subnet-ids <vpc_subnets>
     aws ec2 create-vpc-endpoint --vpc-id <VPC-ID> --service-name com.amazonaws.<aws-region>.s3  --vpc-endpoint-type Gateway --route-table-ids <vpc_route_table>
    
    ```
    

## Create RDS MySQL Database:

1.  Execute the below command to create the database,
    
    ```
     aws rds create-db-instance --db-name mysql_db --db-instance-identifier  mysql-dev --engine mysql --db-instance-class db.m5.large --master-username admin --master-user-password admin123 --engine-version 8.0.16  --publicly-accessible --no-multi-az --enable-iam-database-authentication --allocated-storage 40 
    
    ```
    
2.  Since the database creates on the default VPC, update the security group with port access that’s attached to DB.
    
3.  Update the security group assigned to DB instance to allow 3306 port and use this security group while creating the lambda function.
    
4.  Login to mysql and execute below commands to create user with IAM Authentication and grant permission with create, select and insert.
    
    ```
     CREATE USER {dbusername} IDENTIFIED WITH AWSAuthenticationPlugin as 'RDS';
     GRANT CREATE ON *.* TO '{dbusername}'@'%';
     GRANT INSERT ON *.* TO '{dbusername}'@'%';
     GRANT SELECT ON *.* TO '{dbusername}'@'%';
    
    ```
    
5.  Create a database schema and table in the database and use the info in the parameter store. (Optional)
    

## Create Roles in IAM for executing of lambda and s3 access with RDS:

1.  Create Policy which allows access to below with set of permissions to allow,  
    a. S3 - Read, Write  
    b. RDS Connection Permission - Connect (Update the Resource with DB Resource id from RDS Created)  
    c. SSM Parameter Store - Read, List  
    d. Cloud watch logs - Create, write  
    e. VPC Network Services - Create, List, Delete
    
    ```
     aws iam create-policy --policy-name policy_lambda --policy-document file:///policies_role.json
    
    ```
    
2.  Create a role for lambda execution with permission show in file.
    
    ```
     aws iam create-role --role-name execute_role_lambda --assume-role-policy-document file:///role.json
    
    ```
    
3.  Attach Policy to role,
    
    ```
     aws iam attach-role-policy --role-name execute_role_lambda --policy-arn arn:aws:iam::<aws_account_id>:policy/<role_name>
    
    ```
    

## Create Bucket for Source Files:

1.  Execute below command to create the bucket,
    
    ```
     aws s3api create-bucket --bucket <bucket-name> --create-bucket-configuration LocationConstraint=<aws-region>
    
    ```
    
2.  Assign the bucket policy to restrict the access of bucket to certain roles,(Update the bucket name and roles that need access to bucket)
    
    ```
     aws s3api put-bucket-policy --bucket <bucket-name> --policy file://bucket_policy.json
    
    ```
    

## Create SSM Parameter for lambda connection and config info:

1.  Create parameter in AWS Parameter store with below structure with name RDS\_Mysql\_Secrects (If you choose other name, make changes in the lambda_function code),  
    `{ "dbType": "DB Type", "host": "DB Host Address", "username": "DB User Name", "port": "DB Port", "service_db": "Database Connection service Name", "mysql_schema": "Mysql Schema Name", "mysql_tbl": "Mysql table name", "archiveBucket": "Archive Bucket Name", "archivePath": "Archive Path" }`
    
    ```
    aws ssm put-parameter --name RDS_Mysql_Secrects --type String --value "{'dbType': 'DB Type','host': 'DB Host Address','username': 'DB User Name','port': 'DB Port','service_db': 'Database Connection service Name','mysql_schema': 'Mysql Schema Name','mysql_tbl': 'Mysql table name','archiveBucket': 'Archive Bucket Name','archivePath': 'Archive Path'}"
    
    ```
    

## Creating Lambda Layer for Python Lib:

1.  Create Lambda layer for creating the environment (this layer consists of the packages/dependencies that to perform python task)
    1.  Download the Python library from [https://public-data-analytics.s3.us-east-2.amazonaws.com/lambda\_layers\_lib/python\_lib\_lambda.zip](https://public-data-analytics.s3.us-east-2.amazonaws.com/lambda_layers_lib/python_lib_lambda.zip)
        
    2.  Upload the library to S3 bucket and execute below command,
        
        ```
         aws lambda publish-layer-version --layer-name python_lib --description "My Python layer" --content S3Bucket=<bucket-name>,S3Key=<python-lib-key> --compatible-runtimes python3.6 python3.7
        
        ```
        
    3.  Once the layer is created make a note of the layer arn created, we will be using it in creating the lambda function.
        

## Creating the Lambda Function and assigning the s3 file event trigger:

1.  Zip the below files to create lambda function,
    
    1.  lambda_function.py
    2.  [Ops.py](http://Ops.py)
    3.  rds-combined-ca-bundle.pem
2.  Execute below command to create lambda function with in a VPC,
    
    ```
     aws lambda create-function --function-name loadS3FilestoMysql --runtime python3.7 --zip-file fileb://<code_zip_file_path> --handler lambda_function.lambda_handler --role arn:aws:iam::<aws_account_id>:role/<aws_role_id> --layers <layer arn> --timeout 600 --vpc-config SubnetIds=<vpc-subnets>,SecurityGroupIds=<vpc-secuirty-group>
    
    ```
    
    Use role, layer created before and subnets and security group that are allocated to RDS instance. This will give the private access to RDS resource with VPC.
    
3.  Create the event trigger rule in s3 to lambda, execute below command,
    
    ```
     aws s3api put-bucket-notification-configuration --bucket <bucket-name> --notification-configuration file://s3_notification.json 
    
    ```
    

## Trigger the Lambda function on S3 File create event:

1.  Place a csv file in the bucket path you have mentioned in the put bucket notification configuration.
