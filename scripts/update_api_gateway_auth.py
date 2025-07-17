#!/usr/bin/env python3
"""
Script to update API Gateway to use IAM authentication
This allows the API Gateway to authenticate requests using IAM credentials
"""

import boto3
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def update_api_gateway_auth():
    """Update API Gateway to use IAM authentication"""
    print("=== Updating API Gateway to Use IAM Authentication ===")
    
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
    
    # API Gateway ID (extract from your API endpoint)
    api_endpoint = "https://s8yefd1acg.execute-api.ap-south-1.amazonaws.com"
    if not api_endpoint:
        print("Error: API_ENDPOINT environment variable not found.")
        print("Please make sure your .env file contains the API_ENDPOINT variable.")
        sys.exit(1)
    
    # Extract API ID from the endpoint URL
    try:
        api_id = api_endpoint.split('//')[1].split('.')[0]
        print(f"Extracted API Gateway ID: {api_id}")
    except Exception as e:
        print(f"Error extracting API ID from endpoint URL: {str(e)}")
        print(f"API Endpoint: {api_endpoint}")
        print("Please check the format of your API_ENDPOINT variable.")
        sys.exit(1)
    
    # Initialize API Gateway client
    api_gateway = boto3.client('apigatewayv2')
    
    try:
        # Get all routes
        print(f"Getting routes for API Gateway: {api_id}")
        routes = api_gateway.get_routes(ApiId=api_id)
        
        if not routes.get('Items'):
            print("No routes found for this API Gateway.")
            sys.exit(1)
        
        # Update each route to use IAM authentication
        for route in routes['Items']:
            route_id = route['RouteId']
            route_key = route['RouteKey']
            
            print(f"Updating route: {route_key} (ID: {route_id})")
            
            # Update route to use IAM authentication
            api_gateway.update_route(
                ApiId=api_id,
                RouteId=route_id,
                AuthorizationType='AWS_IAM'
            )
            
            print(f"Successfully updated route {route_key} to use IAM authentication")
        
        # Deploy API to make changes effective
        print("Deploying API to make changes effective...")
        api_gateway.create_deployment(
            ApiId=api_id,
            Description='Deploy IAM authentication'
        )
        
        print("\n=== API Gateway Update Complete ===")
        print("All routes now use IAM authentication.")
        print("Make sure to attach the appropriate IAM policy to your EC2 instance role.")
        
    except Exception as e:
        print(f"Error updating API Gateway: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    update_api_gateway_auth()
