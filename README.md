## AWS Lake Formation Permissions Automation

This is a sample application to automate granting permissions to AWS IAM roles across multiple accounts to provide access to a data in a data lake account via a centralized AWS Glue Data Catalog.

You can use this sample to:

* Use [an AWS Cloudformation template](cfn/create-lob-user-v2.json) to provision a test Athena user in Line-Of-Business (LOB) accounts
* Use another AWS Cloudformation template to create test database and tables in AWS Glue Data Catalog
* Use a third AWS Cloudformation template to deploy AWS Lambda functions and roles to grant permissions to the database and table in your data catalog
* Provision permissions for cross account Athena queries that use manifests using bucket policies



## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
