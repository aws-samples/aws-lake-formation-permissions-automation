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

import boto3
import botocore
import datetime
import time
import json
import sys
import logging

session = boto3.Session()
glue_client = session.client('glue')
lakeformation = session.client('lakeformation')

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

    logger.debug("boto3 version = "+ boto3.__version__)
    logger.debug("botocore version = "+ botocore.__version__)
    logger.debug("grant_lob_permissions received event: " + json.dumps(event, indent=2))

    databaseName    = event['databaseName']
    typeOfChange    = event['typeOfChange']
    cdl_account_id  = event['cdl_account_id']

    logger.debug("databaseName: "+ databaseName)
    logger.debug("typeOfChange:" + typeOfChange)
    
    lob_db_permissions        = event['lob_db_permissions']
    lob_alltables_permissions = event['lob_alltables_permissions']
    lob_account_id            = event['lob_account_id']
    lob_athena_user           = event['lob_athena_user']

    database_resource = {'DatabaseInput': {'Name': databaseName}}
   
    # -----------------------------------------------------------------------
    # 1. Create database resource-link
    # 2. Grant database permissions to lob_athena_user to that resource-link
    # 3. Grant table permissions to lob_athena_user to access tables in the target database(CDL)
    # -----------------------------------------------------------------------
   
   
    logger.debug("granting permissions")
    logger.debug(" *From the LOB account* go to the LakeFormation console as LF Admin and *CREATE* *resource-links* for those databases and tables")

    databaseLink = databaseName  + '-link'
    try:
        glue_client.create_database(
            DatabaseInput= {
                'Name': databaseLink,
                'TargetDatabase': {
                    'CatalogId': cdl_account_id,
                    'DatabaseName': databaseName
                }
            }
        )
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'AlreadyExistsException':
            logger.warn('Database link ' + databaseLink + ' already exists.')
        elif error.response['Error']['Code'] == 'InvalidInputException':
            logger.warn('The input provided was not valid.')
        else:
            raise error
    response = glue_client.get_databases(ResourceShareType='FOREIGN')
    logger.debug("resource-link created: " + str(response))
   
    logger.debug("From the LOB account go to the LakeFormation console as LF Admin and choose the resource link and choose GRANT TO TARGET and choose All tables")

    lob_user_arn = "arn:aws:iam::" + lob_account_id + ":user/" + lob_athena_user
    database_resource = {'Database': {'Name': databaseLink}}
    try:
        lakeformation.grant_permissions(Principal={'DataLakePrincipalIdentifier': lob_user_arn},
                                            Resource=database_resource,
                                            Permissions=lob_db_permissions
                                            )
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'EntityNotFoundException':
            logger.warn('The entity provided was not found.')
        elif error.response['Error']['Code'] == 'InvalidInputException':
            logger.warn('The input provided was not valid.')
        else:
            raise error # For possible Exceptions refer: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lakeformation.html#LakeFormation.Client.grant_permissions

    time.sleep(1)
    
    try:
        lakeformation.grant_permissions(
            Principal={'DataLakePrincipalIdentifier': lob_user_arn},
                                        Resource={
                                            'Table': {
                                                'CatalogId': cdl_account_id, #This is what qualifies the resource link - very important!
                                                'DatabaseName': databaseName,
                                                'TableWildcard': {}
                                            }
                                        },
                                        Permissions=lob_alltables_permissions
                                        )
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'EntityNotFoundException':
            logger.warn('The entity provided was not found.')
        elif error.response['Error']['Code'] == 'InvalidInputException':
            logger.warn('The input provided was not valid.')
        else:
            raise error # For possible Exceptions refer: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lakeformation.html#LakeFormation.Client.grant_permissions
