#!/usr/bin/env python3
"""
Script to add a bucket policy to the S3 bucket to restrict object size
This provides an additional layer of security beyond presigned URLs
"""

import boto3
import json
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

def main():
    """Add a bucket policy to restrict object size"""
    print("=== Adding S3 Bucket Policy for Size Restriction ===")
    
    # Check AWS CLI configuration
    try:
        boto3.setup_default_session()
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()["Account"]
        region = boto3.session.Session().region_name
        print(f"AWS CLI is configured properly.")
        print(f"Using AWS region: {region}")
        print(f"AWS Account ID: {account_id}")
    except Exception as e:
        print(f"Error with AWS CLI configuration: {str(e)}")
        print("Please run 'aws configure' to set up your AWS credentials.")
        sys.exit(1)
    
    # Get bucket name
    bucket_name = os.environ.get('BUCKET_NAME', 'file-sharing-system-mru')
    
    # Create S3 client
    s3_client = boto3.client('s3')
    
    # Create bucket policy
    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "LimitObjectSize",
                "Effect": "Deny",
                "Principal": {"AWS": "*"},
                "Action": "s3:PutObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*",
                "Condition": {
                    "NumericGreaterThan": {
                        "s3:request-maximum-object-size": MAX_FILE_SIZE
                    }
                }
            }
        ]
    }
    
    try:
        # Convert policy to JSON string
        bucket_policy_string = json.dumps(bucket_policy)
        
        # Set bucket policy
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=bucket_policy_string
        )
        
        print(f"Successfully applied size restriction policy to bucket: {bucket_name}")
        print(f"Maximum allowed file size: {MAX_FILE_SIZE / (1024 * 1024):.2f} MB")
        
    except Exception as e:
        print(f"Error applying bucket policy: {str(e)}")
        sys.exit(1)
    
    print("=== Bucket Policy Configuration Complete ===")

if __name__ == "__main__":
    main()
