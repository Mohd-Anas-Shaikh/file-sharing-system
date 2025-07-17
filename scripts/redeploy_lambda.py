#!/usr/bin/env python
"""
Redeploy Lambda Functions Script for File Sharing System

This script redeploys only the Lambda functions with fixed dependencies.
It does not modify any other AWS resources.

Usage:
    python redeploy_lambda.py
"""

import os
import sys
import boto3
import time
import zipfile
import tempfile
import shutil
import json

# AWS Lambda function names
LAMBDA_FUNCTIONS = [
    'file-sharing-upload',
    'file-sharing-download',
    'file-sharing-cleanup'
]

# S3 bucket name
S3_BUCKET_NAME = 'file-sharing-system-mru'

def check_aws_cli():
    """Check if AWS CLI is configured properly"""
    try:
        # Initialize boto3 clients
        lambda_client = boto3.client('lambda')
        lambda_client.list_functions()
        print("AWS CLI is configured properly.")
        return True
    except Exception as e:
        print(f"Error with AWS CLI configuration: {str(e)}")
        print("Please run 'aws configure' to set up your AWS credentials.")
        return False

def package_lambda_function(function_name):
    """Package Lambda function code into a ZIP file"""
    function_dir = f"backend/lambda/{function_name.replace('file-sharing-', '')}"
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

def update_lambda_function(function_name, zip_path):
    """Update Lambda function code"""
    lambda_client = boto3.client('lambda')
    
    try:
        # Update function code
        with open(zip_path, 'rb') as zip_file:
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_file.read()
            )
        print(f"Updated Lambda function code for {function_name}")
        
        # Get function configuration to verify update
        response = lambda_client.get_function(FunctionName=function_name)
        print(f"Function {function_name} last modified: {response['Configuration']['LastModified']}")
        
        return True
    
    except Exception as e:
        print(f"Error updating Lambda function: {str(e)}")
        return False

def main():
    """Main function to redeploy Lambda functions"""
    print("=== File Sharing System - Lambda Redeployment ===")
    
    # Check AWS CLI configuration
    if not check_aws_cli():
        return
    
    # Get AWS region
    session = boto3.session.Session()
    region = session.region_name
    print(f"Using AWS region: {region}")
    
    # Redeploy each Lambda function
    for function_name in LAMBDA_FUNCTIONS:
        print(f"\nRedeploying {function_name}...")
        
        # Package function code
        zip_path = package_lambda_function(function_name)
        if not zip_path:
            print(f"Failed to package {function_name}. Skipping...")
            continue
        
        # Update function code
        if update_lambda_function(function_name, zip_path):
            print(f"Successfully redeployed {function_name}")
        else:
            print(f"Failed to redeploy {function_name}")
    
    print("\n=== Redeployment Complete ===")
    print("Lambda functions have been redeployed with fixed dependencies.")
    print("You can now test the file sharing system again.")

if __name__ == "__main__":
    main()
