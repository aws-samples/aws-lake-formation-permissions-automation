## AWS Lake Formation Permissions Automation

This is a sample application to automate granting permissions to AWS IAM roles across multiple accounts to provide access to a data in a data lake account via a centralized AWS Glue Data Catalog.

You can use this sample to:

* Provision a test Athena user in Line-Of-Business (LOB) accounts
* Create test database and tables in AWS Glue Data Catalog
* Deploy AWS Lambda functions and roles to grant permissions to the database and table in your data catalog
* Provision permissions for cross account Athena queries that use manifests using bucket policies

## Deployment steps
Create AWS Cloudformation stacks in the following order:
1. In each of your Line-Of-Business (LOB) accounts, deploy [cfn/create-lob-user-v2.json](cfn/create-lob-user-v2.json) to provision a test Amazon Athena user
2. In your central data lake account(CDL), deploy [cfn/lf-automation-cfn_v16.json](cfn/lf-automation-cfn_v16.json) to provision AWS Lambda functions and AWS Identity and Access Manager (IAM) roles to grant permissions to the database and table in your data catalog
  This is the stack in which you will provide the account numbers of each of your LOB accounts. Note that this Cloudformation template only accepts a maximum of 4 account IDs as parameters. If you want to grant access to more LOB accounts, you can modify the template to add more accounts. Cloudformation uses these parameters to give the Lambda functions cross account permission to invoke Lambda functions in each of the LOB accounts.
3. In each of your LOB accounts, deploy [cfn/lf-automation-lob-cfn-v6.json](cfn/lf-automation-lob-cfn-v6.json) to provision Lambda function to grant permissions within each account to the Amazon Athena user created in the first step.
  This is the stack in which you will provide the account number of your central data lake as a parameter. Cloudformation uses this parameter to create trust policies in the LOB accounts to trust the CDL account to invoke LOB accounts Lambda function.
Now that all resources have been deployed in the accounts, you can now start testing by invoking the Lambda functions
4. From the Outputs section of lf-automation-cdl stack copy the “JSONForTestingCreateDB” value to create a JSON file called test-db-data-s3-config.json, edit the file to change the name of your database, and invoke the [create_test_db](lambda/create_test_db.py) Lambda function. This will create a test database and table in the Glue Data Catalog.
Here is an example CLI:
```
aws lambda invoke --function-name create_test_db --payload "file://test-db-data-s3-config.json" --cli-binary-format raw-in-base64-out out.txt
```
5. From the Outputs section of lf-automation-cdl stack copy the “JSONForTestingGrantPermissions” value to create a JSON file called lob_permissions.json, edit the file to change the name of your database, and invoke the [grant_permissions](lambda/grant_permissions.py) Lambda function. This will grant permissions to the roles as declared in the JSON file. You can edit the file to add or modify permissions to the roles. You can also add additional roles in the file with appropriate permissions as needed.
Here is an example CLI:
```
aws lambda invoke --function-name grant_permissions --payload "file://lob_permissions.json" --cli-binary-format raw-in-base64-out out.txt
```

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
