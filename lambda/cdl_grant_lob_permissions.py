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
import sys
import botocore.exceptions
import logging

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

session = boto3.Session()
sts = boto3.client('sts')

def lambda_handler(event, context):

    logger.debug("cdl_grant_lob_permissions received event: " + json.dumps(event, indent=2))
    
    databaseARN =event['databaseARN']
    databaseName = event['databaseName']
    typeOfChange = event['typeOfChange']
    cdl_account_id = event['cdl_account_id']
    rolearn = event['ARN']
    lob_arn_region_prefix = event['lob_arn_region_prefix']
    lob_athena_user = event['lob_athena_user']
    
    logger.debug("databaseARN:" + databaseARN)
    logger.debug("databaseName: "+ databaseName)
    logger.debug("typeOfChange:" + typeOfChange)
    logger.debug("cdl_account_id:" + cdl_account_id)
    logger.debug("rolearn:" + rolearn)
    
    # -----------------------------------------------------------------------
    # Assume LOB account role, initiate a session as the LOB role
    # and invoke grant_lob_permissions lambda function from that 
    # account
    # -----------------------------------------------------------------------
    try:
        awsaccount = sts.assume_role(
            RoleArn=rolearn,
            RoleSessionName='awsaccount_session'
        )
    #https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sts.html#STS.Client.assume_role
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'MalformedPolicyDocumentException':
            logger.warn('The policy document is malformed.')
        elif error.response['Error']['Code'] == 'ExpiredTokenException':
            logger.warn('The token has expired.')
        else:
            raise error 

    ACCESS_KEY = awsaccount['Credentials']['AccessKeyId']
    SECRET_KEY = awsaccount['Credentials']['SecretAccessKey']
    SESSION_TOKEN = awsaccount['Credentials']['SessionToken']
    
    start = '::'
    end = ':'
    lob_account_id = rolearn[rolearn.find(start)+len(start):rolearn.rfind(end)] # getting awsaccount ID from IAM Role ARN

    lob_lambda_arn = lob_arn_region_prefix + lob_account_id + ":function:grant_lob_permissions"
    logger.debug("lob_lambda_arn " + lob_lambda_arn)
    lambda_lob_client = boto3.client('lambda', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, aws_session_token=SESSION_TOKEN)
    args = {
        "cdl_account_id": cdl_account_id, 
        "lob_account_id": lob_account_id, 
        "databaseARN": databaseARN, 
        "databaseName": databaseName, 
        "typeOfChange": typeOfChange, 
        "lob_athena_user": lob_athena_user,
        "lob_db_permissions": event['lob_db_permissions'], 
        "lob_alltables_permissions": event['lob_alltables_permissions']
    }
    
    try:
        invoke_response = lambda_lob_client.invoke(FunctionName=lob_lambda_arn,
                                             InvocationType='Event', #assync exec
                                             Payload=json.dumps(args))
    #https://docs.amazonaws.cn/en_us/lambda/latest/dg/API_Invoke.html
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ServiceException':
            logger.warn('The AWS Lambda service encountered an internal error.')
        elif error.response['Error']['Code'] == 'ResourceNotFoundException':
            logger.warn('The resource specified in the request does not exist.')
        else:
            raise error # For possible Exceptions refer: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.invoke
        
   
