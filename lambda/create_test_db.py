# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import json
import boto3
import csv
import botocore.exceptions
import logging

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

def lambda_handler(event, context):
    glue = boto3.client('glue')
    #allow create-table permissions on the role first
    lakeformation = boto3.client('lakeformation')
    org = boto3.client('organizations')
    response = org.describe_organization()
    org_id = response['Organization']['Arn']
    databaseName = event['databaseName']
    tableName = databaseName + "-table"
    symlinkTableName = databaseName + "-symlink-table"
    
    logger.debug("received databaseName from json: " + databaseName)
    try:
        response = glue.create_database(
            DatabaseInput={
                'Name': databaseName,
                'Description': 'Database will have two tables, one for symlink testing and one regular table'
            }
        )
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'AlreadyExistsException':
            logger.warn('Database ' + databaseName + ' already exists.')
        elif error.response['Error']['Code'] == 'InvalidInputException':
            logger.warn('The input provided was not valid.')
        else:
            raise error
            
    # creating CSV data and writing it to a temp file

    emp_rows = [["emp_id", "name", "dept", "salary"],
                 [1, "Ariana Grande", "HR", "60000"],
                 [2, "Shawn Mendes", "IT", "70000"],
                 [3, "Selena Gomez", "IT", "80000"],
                 [4, "Sia Furler", "Sales", "90000"]]
                 
    try:
        with open('/tmp/employees.csv', 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerows(emp_rows)
    except Exception as e:
        logger.warn(e)
        raise e
    
   # CREATING MAIN TEST TABLE USING CSV DATA
   
    s3_data_bucket = event['s3-data-bucket']
    s3_data_folder = event['s3-data-folder']
    s3_data_file = event['s3-data-file']
    
    # Writing CSV file in data folders in the data bucket (for main table testing)
    s3_data_object_key = s3_data_folder + "/" +  s3_data_file
    s3.upload_file('/tmp/employees.csv', s3_data_bucket, s3_data_object_key)
    
    #creating main table
    s3_data_bucket_location = "s3://" + s3_data_bucket + "/" + s3_data_folder
    try:
        create_table_response = glue.create_table(
                DatabaseName= databaseName,
                TableInput={
                'Name': tableName,
                'Description': tableName,
                'StorageDescriptor': {
                    'Columns': [
                        { 'Name': 'emp_id', 'Type': 'string'},
                        { 'Name': 'name', 'Type': 'string'},
                        { 'Name': 'dept', 'Type': 'string'},
                        { 'Name': 'salary', 'Type': 'string'}
                    ],
                    'Location': s3_data_bucket_location, 
                    'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
                    'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
                    'Compressed': False,
                    'SerdeInfo': {
                        'Name': 'OpenCSVSerde',
                        'SerializationLibrary': 'org.apache.hadoop.hive.serde2.OpenCSVSerde',
                        'Parameters': {
                            'separatorChar': ',',
                            "skip.header.line.count":"1"
                        }
                    }
                },
                'TableType' : "EXTERNAL_TABLE"} )
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'AlreadyExistsException':
            logger.warn('Table ' + tableName + ' already exists.')
        elif error.response['Error']['Code'] == 'InvalidInputException':
            logger.warn('The input provided was not valid.')
        elif error.response['Error']['Code'] == 'EntityNotFoundException':
            logger.warn('A specified entity does not exist.')
        else:
            raise error

    # CREATING SYMLINK FILES TEST TABLE  USING CSV DATA
    
    s3_symlink_bucket = event['s3-symlink-bucket']
    s3_symlink_folder = event['s3-symlink-folder']
    s3_symlink_file = event['s3-symlink-file']
    # Writing CSV file in data folders in symlink bucket (for symlink table testing)
    s3_data_object_key = s3_data_folder + "/" +  s3_data_file
    s3.upload_file('/tmp/employees.csv', s3_symlink_bucket, s3_data_object_key)
    
    # creating symlink text file with pointer to the CSV data file creates above
    symlink_string = "s3://" + s3_symlink_bucket + "/" + s3_data_object_key  
    with open("/tmp/symlink.txt", "w") as symlink_file: 
        symlink_file.write(symlink_string) 
    s3_symlink_object_key = s3_symlink_folder + "/" + s3_symlink_file
    s3.upload_file('/tmp/symlink.txt', s3_symlink_bucket, s3_symlink_object_key)
    
    #creating symlink table
    s3_symlink_bucket_location = "s3://" + s3_symlink_bucket + "/" + s3_symlink_folder 
    try:
        create_symlink_table_response = glue.create_table(
                DatabaseName= databaseName,
                TableInput={
                'Name': symlinkTableName,
                'Description': symlinkTableName,
                'StorageDescriptor': {
                    'Columns': [
                        { 'Name': 'emp_id', 'Type': 'string'},
                        { 'Name': 'name', 'Type': 'string'},
                        { 'Name': 'dept', 'Type': 'string'},
                        { 'Name': 'salary', 'Type': 'string'}
                        ],
                    'Location': s3_symlink_bucket_location, 
                    'InputFormat': 'org.apache.hadoop.hive.ql.io.SymlinkTextInputFormat',
                    'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
                    'Compressed': False,
                    'SerdeInfo': {
                        'Name': 'OpenCSVSerde',
                        'SerializationLibrary': 'org.apache.hadoop.hive.serde2.OpenCSVSerde',
                        'Parameters': {
                            'separatorChar': ',',
                            "skip.header.line.count":"1"
                        }
                    }
                },
                'TableType' : "EXTERNAL_TABLE"} )
                
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'AlreadyExistsException':
            logger.warn('Table ' + tableName + ' already exists.')
        elif error.response['Error']['Code'] == 'InvalidInputException':
            logger.warn('The input provided was not valid.')
        elif error.response['Error']['Code'] == 'EntityNotFoundException':
            logger.warn('A specified entity does not exist.')
        else:
            raise error

    
           