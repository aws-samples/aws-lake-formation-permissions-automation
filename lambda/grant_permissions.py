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
import json
import botocore.exceptions
import logging

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

session = boto3.Session()

lambda_client = boto3.client('lambda')
sts = boto3.client('sts')

def lambda_handler(event, context):

    logger.debug("grant_permissions lambda received event: " + json.dumps(event, indent=2))
    databaseARN = "databaseARN"
    logger.debug("databaseARN: " + databaseARN)
    databaseName = event['databaseName']
    logger.debug("databaseName: " + databaseName)
    typeOfChange = event['typeOfChange']
    logger.debug('typeOfChange = %s' % (typeOfChange))
    
    # -----------------------------------------------------------------------
    # Invoke a lambda function to share permissions with the AWS Org
    # -----------------------------------------------------------------------

    #cdl_account_id = event['account']
    cdl_account_id = sts.get_caller_identity().get('Account')
    cdl_region = session.region_name
    cdl_lambda_function_arn = "arn:aws:lambda:" + cdl_region + ":" + cdl_account_id + ":function:cdl_grant_org_permissions"

    rolearnlist = []
    database_resource = {'Database': {'Name': databaseName}}
    
    logger.debug("invoking cdl lambda")
    try:
        invoke_cdl_response = lambda_client.invoke(FunctionName=cdl_lambda_function_arn, #"arn:aws:lambda:us-east-1:111111111111:function:setup_cdl_lf_permissions",
                                        #  InvocationType='Event', #assync exec
                                         InvocationType='RequestResponse', #sync exec
                                         Payload=json.dumps(event)) #pass the event
        logger.debug(invoke_cdl_response)
    #https://docs.amazonaws.cn/en_us/lambda/latest/dg/API_Invoke.html
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ServiceException':
            logger.warn('The AWS Lambda service encountered an internal error.')
        elif error.response['Error']['Code'] == 'ResourceNotFoundException':
            logger.warn('The resource specified in the request does not exist.')
        else:
            raise error # For possible Exceptions refer: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.invoke

    # -----------------------------------------------------------------------
    # Loop through the list of LOB ARNs, for each ARN in the list:
    # asynchronously invoke cdl_grant_lob_permissions lambda and pass ARN
    # -----------------------------------------------------------------------
    
    for role in event['roles']:
        logger.debug("role: " + str(role))
        rolearn = role['arn']
        start = '::'
        end = ':'
        lob_account_id = rolearn[rolearn.find(start)+len(start):rolearn.rfind(end)] # getting awsaccount ID from IAM Role ARN
        lob_athena_user = role['lob_athena_user']
        lob_db_permissions = role['lob_db_permissions']
        lob_alltables_permissions = role['lob_alltables_permissions']
        lob_region = role['lob_region']
        lob_arn_region_prefix = "arn:aws:lambda:" + lob_region + ":"
        args = {
            "ARN": rolearn, 
            "lob_account_id": lob_account_id, 
            "cdl_account_id": cdl_account_id, 
            "databaseARN": databaseARN, 
            "databaseName": databaseName, 
            "typeOfChange": typeOfChange, 
            "lob_athena_user": lob_athena_user,
            "lob_db_permissions": lob_db_permissions, 
            "lob_alltables_permissions": lob_alltables_permissions,
            "lob_arn_region_prefix": lob_arn_region_prefix
        }
        try:
            invoke_response = lambda_client.invoke(FunctionName="cdl_grant_lob_permissions",
                                             InvocationType='Event', #assync exec
                                             #InvocationType='RequestResponse', #sync exec
                                             Payload=json.dumps(args))
        #https://docs.amazonaws.cn/en_us/lambda/latest/dg/API_Invoke.html
        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'ServiceException':
                logger.warn('The AWS Lambda service encountered an internal error.')
            elif error.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.warn('The resource specified in the request does not exist.')
            else:
                raise error # For possible Exceptions refer: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.invoke

