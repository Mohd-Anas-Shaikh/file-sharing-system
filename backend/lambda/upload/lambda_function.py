import json
import boto3
import os
import uuid
import logging
import time
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client outside the handler for container reuse
s3_client = boto3.client('s3')
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'file-sharing-system')

# Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain', 'text/csv', 'application/zip', 'application/x-zip-compressed',
    'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'video/mp4', 'video/quicktime', 'audio/mpeg', 'audio/mp4'
]
UPLOAD_URL_EXPIRY = 300  # 5 minutes
MAX_RETRIES = 3

def s3_put_with_retry(bucket, key, body=None, metadata=None, content_type=None, max_retries=MAX_RETRIES):
    """Put an object to S3 with retry logic for transient failures"""
    if metadata is None:
        metadata = {}
    
    retries = 0
    while retries < max_retries:
        try:
            params = {
                'Bucket': bucket,
                'Key': key
            }
            
            if body is not None:
                params['Body'] = body
            
            if content_type is not None:
                params['ContentType'] = content_type
                
            if metadata:
                params['Metadata'] = metadata
                
            s3_client.put_object(**params)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['SlowDown', 'InternalError', 'ServiceUnavailable']:
                retries += 1
                if retries < max_retries:
                    # Exponential backoff
                    sleep_time = 2 ** retries
                    logger.warning(f"S3 operation failed with {error_code}. Retrying in {sleep_time}s. Attempt {retries}/{max_retries}")
                    time.sleep(sleep_time)
                    continue
            logger.error(f"S3 operation failed: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in S3 operation: {str(e)}", exc_info=True)
            raise

def generate_upload_url(file_id, filename, content_type, file_size):
    """Generate a presigned POST for direct upload to S3 with size restrictions"""
    s3_key = f"{file_id}/{filename}"
    try:
        # Create conditions for the presigned POST
        conditions = [
            {"content-type": content_type},
            ["content-length-range", 0, MAX_FILE_SIZE]  # Restrict file size
        ]
        
        # Generate presigned POST
        presigned_post = s3_client.generate_presigned_post(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Fields={
                'Content-Type': content_type
            },
            Conditions=conditions,
            ExpiresIn=UPLOAD_URL_EXPIRY
        )
        
        # Log the creation of presigned POST
        logger.info(f"Generated presigned POST for file: {filename}, ID: {file_id}, max size: {MAX_FILE_SIZE} bytes")
        
        return presigned_post
    except Exception as e:
        logger.error(f"Error generating presigned POST: {str(e)}", exc_info=True)
        raise

def lambda_handler(event, context):
    """
    AWS Lambda function to handle file uploads to S3
    
    This optimized version:
    1. Generates a presigned URL for direct upload to S3
    2. Validates file size and content type
    3. Uses structured logging
    4. Implements retry logic for S3 operations
    5. Consolidates metadata storage
    
    Expected input:
    - filename (required)
    - content_type (required)
    - file_size (required, in bytes)
    
    Returns:
    - upload_url: Presigned URL for direct upload
    - file_id: Unique identifier for the file
    - download_path: Path to download the file
    - expiration_time: When the file will expire
    """
    request_time = datetime.utcnow().isoformat()
    logger.info(f"Upload request received at {request_time}")
    
    try:
        # Parse request body
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # Validate required fields
        filename = body.get('filename')
        content_type = body.get('content_type')
        file_size = body.get('file_size')
        
        if not filename:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Filename is required'})
            }
            
        if not content_type:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Content type is required'})
            }
            
        if not file_size or not isinstance(file_size, int):
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Valid file size is required'})
            }
        
        # Validate file size
        if file_size > MAX_FILE_SIZE:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': f'File size exceeds the maximum limit of {MAX_FILE_SIZE/1024/1024}MB'})
            }
            
        # Validate content type
        if content_type not in ALLOWED_CONTENT_TYPES:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': f'Content type {content_type} is not allowed'})
            }
        
        # Generate a unique file ID
        file_id = str(uuid.uuid4())
        logger.info(f"Generated file ID: {file_id} for file: {filename}")
        
        # Calculate expiration time (24 hours from now)
        expiration_time = datetime.utcnow() + timedelta(hours=24)
        expiration_timestamp = expiration_time.isoformat()
        
        # Store metadata in S3
        metadata = {
            'original_filename': filename,
            'content_type': content_type,
            'expiration_time': expiration_timestamp,
            'upload_time': datetime.utcnow().isoformat(),
            'file_size': str(file_size)
        }
        
        # Store metadata as a JSON file
        s3_put_with_retry(
            bucket=BUCKET_NAME,
            key=f"{file_id}/metadata.json",
            body=json.dumps(metadata),
            content_type='application/json'
        )
        
        # Generate presigned POST for direct upload with size restriction
        upload_data = generate_upload_url(file_id, filename, content_type, file_size)
        
        # Generate download path
        download_path = f"/download/{file_id}"
        
        logger.info(f"Successfully processed upload request for file ID: {file_id}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'file_id': file_id,
                'upload_data': upload_data,  # Contains url and fields for presigned POST
                'download_path': download_path,
                'expiration_time': expiration_timestamp
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing upload request: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'An internal server error occurred'})
        }
