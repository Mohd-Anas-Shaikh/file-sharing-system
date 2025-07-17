#!/usr/bin/env python
"""
AWS Resources Setup Script for File Sharing System

This script helps to set up the required AWS resources for the file sharing system:
1. S3 Bucket
2. Lambda Functions
3. API Gateway
4. IAM Roles and Policies

Prerequisites:
- AWS CLI installed and configured
- Python 3.8+
- Required Python packages: boto3

Usage:
    python setup_aws_resources.py
"""

import os
import sys
import json
import boto3
import time
import zipfile
import tempfile
import shutil
from datetime import datetime

def check_aws_cli():
    """Check if AWS CLI is configured properly"""
    try:
        # Initialize boto3 clients
        s3 = boto3.client('s3')
        s3.list_buckets()
        print("AWS CLI is configured properly.")
        return True
    except Exception as e:
        print(f"Error with AWS CLI configuration: {str(e)}")
        print("Please run 'aws configure' to set up your AWS credentials.")
        return False

def create_s3_bucket(bucket_name, region=None):
    """Create an S3 bucket for file storage"""
    s3 = boto3.client('s3')
    
    # Check if bucket already exists
    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"Bucket {bucket_name} already exists.")
        return bucket_name
    except:
        pass
    
    try:
        # Create bucket with the specified region or default region
        if region is None:
            s3.create_bucket(Bucket=bucket_name)
        else:
            location = {'LocationConstraint': region}
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration=location
            )
        
        print(f"Created S3 bucket: {bucket_name}")
        
        # Set lifecycle policy to delete expired objects
        lifecycle_config = {
            'Rules': [
                {
                    'ID': 'ExpireAfter24Hours',
                    'Status': 'Enabled',
                    'Filter': {
                        'Prefix': ''
                    },
                    'Expiration': {
                        'Days': 2  # Set to 2 days as a safety net (our Lambda will handle 24 hour expiry)
                    }
                }
            ]
        }
        
        s3.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration=lifecycle_config
        )
        
        print(f"Set lifecycle policy on bucket {bucket_name}")
        return bucket_name
    
    except Exception as e:
        print(f"Error creating S3 bucket: {str(e)}")
        return None

def create_lambda_role():
    """Create IAM role for Lambda functions"""
    iam = boto3.client('iam')
    role_name = 'file-sharing-lambda-role'
    
    # Check if role already exists
    try:
        response = iam.get_role(RoleName=role_name)
        print(f"Role {role_name} already exists.")
        return response['Role']['Arn']
    except:
        pass
    
    try:
        # Create trust relationship policy document
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        # Create role
        response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for file sharing system Lambda functions'
        )
        
        role_arn = response['Role']['Arn']
        print(f"Created IAM role: {role_name}")
        
        # Attach policies
        policies = [
            'arn:aws:iam::aws:policy/AmazonS3FullAccess',
            'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        ]
        
        for policy_arn in policies:
            iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
            print(f"Attached policy {policy_arn} to role {role_name}")
        
        # Wait for role to propagate
        print("Waiting for role to propagate...")
        time.sleep(10)
        
        return role_arn
    
    except Exception as e:
        print(f"Error creating IAM role: {str(e)}")
        return None

def package_lambda_function(function_name):
    """Package Lambda function code into a ZIP file"""
    function_dir = f"backend/lambda/{function_name}"
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Copy function code
        shutil.copy(f"{function_dir}/lambda_function.py", temp_dir)
        
        # Install dependencies
        os.system(f"pip install -r backend/requirements.txt -t {temp_dir}")
        
        # Create ZIP file
        zip_path = f"{temp_dir}/{function_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.zip'):
                        continue
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        
        return zip_path
    
    except Exception as e:
        print(f"Error packaging Lambda function: {str(e)}")
        return None
    
def create_lambda_function(function_name, role_arn, bucket_name):
    """Create Lambda function"""
    lambda_client = boto3.client('lambda')
    function_full_name = f"file-sharing-{function_name}"
    
    # Check if function already exists
    try:
        lambda_client.get_function(FunctionName=function_full_name)
        print(f"Lambda function {function_full_name} already exists.")
        
        # Update function code
        zip_path = package_lambda_function(function_name)
        with open(zip_path, 'rb') as zip_file:
            lambda_client.update_function_code(
                FunctionName=function_full_name,
                ZipFile=zip_file.read()
            )
        print(f"Updated Lambda function code for {function_full_name}")
        
        return function_full_name
    except:
        pass
    
    try:
        # Package function code
        zip_path = package_lambda_function(function_name)
        
        if not zip_path:
            return None
        
        # Create function
        with open(zip_path, 'rb') as zip_file:
            response = lambda_client.create_function(
                FunctionName=function_full_name,
                Runtime='python3.9',
                Role=role_arn,
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_file.read()},
                Timeout=30,
                MemorySize=256,
                Environment={
                    'Variables': {
                        'BUCKET_NAME': bucket_name
                    }
                }
            )
        
        print(f"Created Lambda function: {function_full_name}")
        return function_full_name
    
    except Exception as e:
        print(f"Error creating Lambda function: {str(e)}")
        return None

def create_api_gateway(lambda_functions):
    """Create API Gateway for Lambda functions"""
    api_gateway = boto3.client('apigatewayv2')
    lambda_client = boto3.client('lambda')
    
    api_name = 'file-sharing-api'
    
    # Check if API already exists
    try:
        apis = api_gateway.get_apis()
        for api in apis.get('Items', []):
            if api['Name'] == api_name:
                print(f"API Gateway {api_name} already exists.")
                return api['ApiEndpoint']
    except:
        pass
    
    try:
        # Create HTTP API
        response = api_gateway.create_api(
            Name=api_name,
            ProtocolType='HTTP',
            CorsConfiguration={
                'AllowOrigins': ['*'],
                'AllowMethods': ['GET', 'POST', 'OPTIONS'],
                'AllowHeaders': ['Content-Type', 'Authorization'],
                'MaxAge': 300
            }
        )
        
        api_id = response['ApiId']
        print(f"Created API Gateway: {api_name} (ID: {api_id})")
        
        # Create routes for each Lambda function
        for function_name in lambda_functions:
            if function_name == 'upload':
                route_key = 'POST /upload'
            elif function_name == 'download':
                route_key = 'GET /download/{file_id}'
            else:
                continue
            
            function_full_name = f"file-sharing-{function_name}"
            function_info = lambda_client.get_function(FunctionName=function_full_name)
            function_arn = function_info['Configuration']['FunctionArn']
            
            # Create integration
            integration = api_gateway.create_integration(
                ApiId=api_id,
                IntegrationType='AWS_PROXY',
                IntegrationMethod='POST',
                PayloadFormatVersion='2.0',
                IntegrationUri=function_arn
            )
            
            # Create route
            api_gateway.create_route(
                ApiId=api_id,
                RouteKey=route_key,
                Target=f"integrations/{integration['IntegrationId']}"
            )
            
            print(f"Created route {route_key} for function {function_full_name}")
            
            # Add permission for API Gateway to invoke Lambda
            try:
                lambda_client.add_permission(
                    FunctionName=function_full_name,
                    StatementId=f"{function_name}-api-gateway-permission",
                    Action='lambda:InvokeFunction',
                    Principal='apigateway.amazonaws.com',
                    SourceArn=f"arn:aws:execute-api:{boto3.session.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:{api_id}/*"
                )
                print(f"Added permission for API Gateway to invoke {function_full_name}")
            except lambda_client.exceptions.ResourceConflictException:
                print(f"Permission already exists for {function_full_name}")
        
        # Deploy API
        deployment = api_gateway.create_deployment(
            ApiId=api_id
        )
        
        stage = api_gateway.create_stage(
            ApiId=api_id,
            StageName='$default',
            AutoDeploy=True
        )
        
        api_endpoint = f"https://{api_id}.execute-api.{boto3.session.Session().region_name}.amazonaws.com"
        print(f"Deployed API Gateway: {api_endpoint}")
        
        return api_endpoint
    
    except Exception as e:
        print(f"Error creating API Gateway: {str(e)}")
        return None

def create_cloudwatch_event_rule(lambda_function_name):
    """Create CloudWatch Event Rule to trigger cleanup Lambda function"""
    events = boto3.client('events')
    lambda_client = boto3.client('lambda')
    
    rule_name = 'file-sharing-cleanup-schedule'
    
    try:
        # Create rule
        response = events.put_rule(
            Name=rule_name,
            ScheduleExpression='rate(1 hour)',
            State='ENABLED',
            Description='Trigger file cleanup Lambda function every hour'
        )
        
        rule_arn = response['RuleArn']
        print(f"Created CloudWatch Event Rule: {rule_name}")
        
        # Get Lambda function ARN
        function_info = lambda_client.get_function(FunctionName=lambda_function_name)
        function_arn = function_info['Configuration']['FunctionArn']
        
        # Add target
        events.put_targets(
            Rule=rule_name,
            Targets=[
                {
                    'Id': '1',
                    'Arn': function_arn
                }
            ]
        )
        
        print(f"Added Lambda function {lambda_function_name} as target for rule {rule_name}")
        
        # Add permission for CloudWatch Events to invoke Lambda
        try:
            lambda_client.add_permission(
                FunctionName=lambda_function_name,
                StatementId='cloudwatch-event-permission',
                Action='lambda:InvokeFunction',
                Principal='events.amazonaws.com',
                SourceArn=rule_arn
            )
            print(f"Added permission for CloudWatch Events to invoke {lambda_function_name}")
        except lambda_client.exceptions.ResourceConflictException:
            print(f"Permission already exists for {lambda_function_name}")
        
        return rule_arn
    
    except Exception as e:
        print(f"Error creating CloudWatch Event Rule: {str(e)}")
        return None

def create_env_file(api_endpoint):
    """Create .env file for frontend"""
    env_content = f"""# API Gateway endpoint
API_ENDPOINT={api_endpoint}

# Flask configuration
SECRET_KEY=your-secret-key-here
PORT=5000
"""
    
    with open('frontend/.env', 'w') as f:
        f.write(env_content)
    
    print("Created .env file for frontend")

def main():
    """Main function to set up AWS resources"""
    print("=== File Sharing System - AWS Resources Setup ===")
    
    # Check AWS CLI configuration
    if not check_aws_cli():
        return
    
    # Get AWS region
    session = boto3.session.Session()
    region = session.region_name
    print(f"Using AWS region: {region}")
    
    # Create S3 bucket
    bucket_name = input("Enter a name for your S3 bucket (lowercase, no spaces): ")
    if not bucket_name:
        bucket_name = f"file-sharing-system-{int(time.time())}"
    
    bucket_name = create_s3_bucket(bucket_name, region)
    if not bucket_name:
        return
    
    # Create IAM role for Lambda functions
    role_arn = create_lambda_role()
    if not role_arn:
        return
    
    # Create Lambda functions
    lambda_functions = ['upload', 'download', 'cleanup']
    created_functions = []
    
    for function_name in lambda_functions:
        function_full_name = create_lambda_function(function_name, role_arn, bucket_name)
        if function_full_name:
            created_functions.append(function_name)
    
    if not created_functions:
        print("Failed to create Lambda functions.")
        return
    
    # Create API Gateway for upload and download functions
    api_endpoint = create_api_gateway(['upload', 'download'])
    if not api_endpoint:
        print("Failed to create API Gateway.")
        return
    
    # Create CloudWatch Event Rule for cleanup function
    if 'cleanup' in created_functions:
        rule_arn = create_cloudwatch_event_rule('file-sharing-cleanup')
    
    # Create .env file for frontend
    create_env_file(api_endpoint)
    
    # Output results
    print("\n=== Setup Complete ===")
    print(f"S3 Bucket: {bucket_name}")
    print(f"Lambda Functions: {', '.join(['file-sharing-' + f for f in created_functions])}")
    print(f"API Gateway Endpoint: {api_endpoint}")
    print("\nAPI Endpoints:")
    print(f"- Upload: {api_endpoint}/upload")
    print(f"- Download: {api_endpoint}/download/{{file_id}}")
    
    print("\nNext steps:")
    print("1. Update the frontend to use the new API endpoints")
    print("2. Deploy the frontend")
    print("3. Test the file sharing system")

if __name__ == "__main__":
    main()
