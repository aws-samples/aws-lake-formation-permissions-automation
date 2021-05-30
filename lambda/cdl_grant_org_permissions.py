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
import os
import logging

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

session = boto3.Session()
glue = session.client('glue')
lakeformation = session.client('lakeformation')
lambda_create_test_table = boto3.client('lambda')
org = boto3.client('organizations')
sts = boto3.client('sts')

def lambda_handler(event, context):
    logger.debug("boto3 version = "+ boto3.__version__)
    logger.debug("botocore version = "+ botocore.__version__)

    logger.debug("cdl_grant_org_permissions received event: " + json.dumps(event, indent=2))
    databaseName = event['databaseName']
    typeOfChange = event['typeOfChange']
    logger.debug("databaseName: "+ databaseName)
    logger.debug("typeOfChange:" + typeOfChange)
    # -----------------------------------------------------------------------
    # Retrieving the ID of this account's AWS Organization and 
    # granting permissions to all the accounts in this Org.
    # -----------------------------------------------------------------------

    response = org.describe_organization()
    org_id = response['Organization']['Arn']
    logger.debug("org_id: " + org_id)

    database_resource = {'Database': {'Name': databaseName}}

    logger.debug("granting permissions")
    cdl_permissions = event['cdl_permissions']
    cdl_grantable_permissions = event['cdl_grantable_permissions']
    try:
        response = lakeformation.grant_permissions(Principal={'DataLakePrincipalIdentifier': org_id},
                                        Resource={
                                            'Table': {
                                                'DatabaseName': databaseName,
                                                'TableWildcard': {}
                                            }
                                        },
                                        Permissions=cdl_permissions,
                                        PermissionsWithGrantOption=cdl_grantable_permissions
                                        )
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'EntityNotFoundException':
            logger.warn('The entity provided was not found.')
        elif error.response['Error']['Code'] == 'InvalidInputException':
            logger.warn('The input provided was not valid.')
        else:
            raise error # For possible Exceptions refer: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lakeformation.html#LakeFormation.Client.grant_permissions

    