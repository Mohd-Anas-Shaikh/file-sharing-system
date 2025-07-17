import json
import boto3
import os
from datetime import datetime

# Initialize S3 client
s3_client = boto3.client('s3')
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'file-sharing-system')

def lambda_handler(event, context):
    """
    AWS Lambda function to clean up expired files in S3
    This function is triggered by a scheduled CloudWatch event (every hour)
    """
    try:
        print(f"Starting cleanup of expired files in bucket {BUCKET_NAME}")
        
        # List all objects with metadata.json suffix
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=BUCKET_NAME, Delimiter='/')
        
        # Keep track of deleted files
        deleted_count = 0
        checked_count = 0
        
        # Process each "directory" (file_id prefix)
        for page in pages:
            if 'CommonPrefixes' in page:
                for prefix in page['CommonPrefixes']:
                    file_id = prefix['Prefix'].rstrip('/')
                    checked_count += 1
                    
                    # Check if metadata exists
                    try:
                        metadata_response = s3_client.get_object(
                            Bucket=BUCKET_NAME,
                            Key=f"{file_id}/metadata.json"
                        )
                        metadata_content = metadata_response['Body'].read().decode('utf-8')
                        metadata = json.loads(metadata_content)
                        
                        # Check if file has expired
                        expiration_time = datetime.fromisoformat(metadata['expiration_time'])
                        current_time = datetime.utcnow()
                        
                        if current_time > expiration_time:
                            print(f"File {file_id} has expired. Deleting...")
                            
                            # Delete all objects with this file_id prefix
                            objects_to_delete = []
                            file_paginator = s3_client.get_paginator('list_objects_v2')
                            file_pages = file_paginator.paginate(Bucket=BUCKET_NAME, Prefix=f"{file_id}/")
                            
                            for file_page in file_pages:
                                if 'Contents' in file_page:
                                    for obj in file_page['Contents']:
                                        objects_to_delete.append({'Key': obj['Key']})
                            
                            if objects_to_delete:
                                s3_client.delete_objects(
                                    Bucket=BUCKET_NAME,
                                    Delete={'Objects': objects_to_delete}
                                )
                                deleted_count += 1
                                print(f"Deleted {len(objects_to_delete)} objects for file {file_id}")
                    
                    except Exception as e:
                        print(f"Error processing file {file_id}: {str(e)}")
        
        print(f"Cleanup completed. Checked {checked_count} files, deleted {deleted_count} expired files.")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Cleanup completed. Checked {checked_count} files, deleted {deleted_count} expired files.'
            })
        }
        
    except Exception as e:
        print(f"Error in cleanup function: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'An error occurred: {str(e)}'
            })
        }
