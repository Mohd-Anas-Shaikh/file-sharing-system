# AWS Resources

## S3 Bucket
- Name: file-sharing-system-mru
- Region: ap-south-1
- Purpose: Stores uploaded files and metadata

## Lambda Functions
- Name: file-sharing-upload
- Name: file-sharing-download
- Name: file-sharing-cleanup
- Runtime: Python 3.9
- Region: ap-south-1
- Purpose: Handle file uploads, downloads, and cleanup operations

## API Gateway
- Name: file-sharing-api
- ID: s8yefd1acg
- Endpoint: https://anas-api-gateway
- Region: ap-south-1
- Routes:
  - POST /upload -> file-sharing-upload
  - GET /download/{file_id} -> file-sharing-download

## CloudWatch Event Rule
- Name: file-sharing-cleanup-schedule
- Purpose: Triggers the cleanup Lambda function every hour
- Target: file-sharing-cleanup Lambda function
