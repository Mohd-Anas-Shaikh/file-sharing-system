#!/usr/bin/env python3
"""
Script to delete the cleanup Lambda function and its associated resources
This simplifies the architecture by relying solely on S3 lifecycle policies for file expiration
"""

import boto3
import json
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Delete the cleanup Lambda function and its associated resources"""
    print("=== Deleting Cleanup Lambda Function and Associated Resources ===")
    
    # Check AWS CLI configuration
    try:
        boto3.setup_default_session()
        region = boto3.session.Session().region_name
        print(f"AWS CLI is configured properly.")
        print(f"Using AWS region: {region}")
    except Exception as e:
        print(f"Error with AWS CLI configuration: {str(e)}")
        print("Please run 'aws configure' to set up your AWS credentials.")
        sys.exit(1)
    
    # Resource names
    lambda_function_name = "file-sharing-cleanup"
    rule_name = "file-sharing-cleanup-schedule"
    
    # Create clients
    lambda_client = boto3.client('lambda')
    events_client = boto3.client('events')
    
    # Step 1: Delete the CloudWatch Event Rule
    try:
        print(f"Removing targets from CloudWatch Event Rule: {rule_name}")
        events_client.remove_targets(
            Rule=rule_name,
            Ids=['1']  # Default target ID
        )
        
        print(f"Deleting CloudWatch Event Rule: {rule_name}")
        events_client.delete_rule(
            Name=rule_name
        )
        print(f"Successfully deleted CloudWatch Event Rule: {rule_name}")
    except Exception as e:
        print(f"Error deleting CloudWatch Event Rule: {str(e)}")
        print("Continuing with Lambda function deletion...")
    
    # Step 2: Delete the Lambda function
    try:
        print(f"Deleting Lambda function: {lambda_function_name}")
        lambda_client.delete_function(
            FunctionName=lambda_function_name
        )
        print(f"Successfully deleted Lambda function: {lambda_function_name}")
    except Exception as e:
        print(f"Error deleting Lambda function: {str(e)}")
        sys.exit(1)
    
    print("\n=== Cleanup Complete ===")
    print("The cleanup Lambda function and its associated CloudWatch Event Rule have been deleted.")
    print("File expiration will now be handled solely by the S3 bucket lifecycle policy.")
    print("This simplifies the architecture while maintaining the same functionality.")

if __name__ == "__main__":
    main()
