import json
import boto3
import os
import logging
import time
from datetime import datetime
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client outside the handler for container reuse
s3_client = boto3.client('s3')
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'file-sharing-system')

# Configuration
DOWNLOAD_URL_EXPIRY = 900  # 15 minutes
MAX_RETRIES = 3

def s3_get_with_retry(bucket, key, max_retries=MAX_RETRIES):
    """Get an object from S3 with retry logic for transient failures"""
    retries = 0
    while retries < max_retries:
        try:
            response = s3_client.get_object(Bucket=bucket, Key=key)
            return response
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                # File doesn't exist, no need to retry
                logger.warning(f"File not found: {key}")
                return None
            elif error_code in ['SlowDown', 'InternalError', 'ServiceUnavailable']:
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

def generate_download_url(file_id, filename):
    """Generate a presigned URL for downloading from S3"""
    s3_key = f"{file_id}/{filename}"
    try:
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': s3_key,
                'ResponseContentDisposition': f'attachment; filename="{filename}"'
            },
            ExpiresIn=DOWNLOAD_URL_EXPIRY
        )
        return presigned_url
    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}", exc_info=True)
        raise

def is_file_expired(expiration_time):
    """Check if a file has expired based on its expiration timestamp"""
    try:
        expiration_datetime = datetime.fromisoformat(expiration_time)
        current_time = datetime.utcnow()
        return current_time > expiration_datetime
    except Exception as e:
        logger.error(f"Error checking file expiration: {str(e)}", exc_info=True)
        # If we can't parse the expiration time, assume it's expired for safety
        return True

def lambda_handler(event, context):
    """
    AWS Lambda function to handle file downloads from S3
    
    This optimized version:
    1. Generates a presigned URL for direct download from S3
    2. Validates file existence and expiration
    3. Uses structured logging
    4. Implements retry logic for S3 operations
    
    Expected input:
    - file_id from path parameters
    
    Returns:
    - download_url: Presigned URL for direct download
    - filename: Original filename
    - content_type: File's content type
    - expiration_time: When the file will expire
    """
    request_time = datetime.utcnow().isoformat()
    logger.info(f"Download request received at {request_time}")
    
    try:
        # Get file ID from path parameters
        file_id = event['pathParameters']['file_id']
        logger.info(f"Processing download request for file ID: {file_id}")
        
        # Get metadata
        metadata_key = f"{file_id}/metadata.json"
        metadata_response = s3_get_with_retry(BUCKET_NAME, metadata_key)
        
        if not metadata_response:
            logger.warning(f"Metadata not found for file ID: {file_id}")
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'File not found'})
            }
        
        # Parse metadata
        metadata = json.loads(metadata_response['Body'].read().decode('utf-8'))
        original_filename = metadata.get('original_filename')
        content_type = metadata.get('content_type')
        expiration_time = metadata.get('expiration_time')
        
        # Check if file has expired
        if is_file_expired(expiration_time):
            logger.warning(f"File with ID {file_id} has expired")
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'File has expired'})
            }
        
        # Check if the actual file exists
        file_key = f"{file_id}/{original_filename}"
        file_exists_response = s3_client.head_object(Bucket=BUCKET_NAME, Key=file_key)
        
        if not file_exists_response:
            logger.warning(f"File content not found for file ID: {file_id}")
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'File content not found'})
            }
        
        # Generate presigned URL for download
        download_url = generate_download_url(file_id, original_filename)
        
        logger.info(f"Successfully generated download URL for file ID: {file_id}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'download_url': download_url,
                'filename': original_filename,
                'content_type': content_type,
                'expiration_time': expiration_time
            })
        }
        
    except KeyError as e:
        logger.error(f"Missing required parameter: {str(e)}", exc_info=True)
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': f'Missing required parameter: {str(e)}'})
        }
        
    except Exception as e:
        logger.error(f"Error processing download request: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'An internal server error occurred'})
        }
