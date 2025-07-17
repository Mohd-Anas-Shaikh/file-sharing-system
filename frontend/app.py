from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import os
import requests
import json
import io
import time
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')

# API Gateway URL
API_ENDPOINT = os.getenv('API_ENDPOINT', 'http://localhost:3000')
UPLOAD_URL = f"{API_ENDPOINT}/upload"
DOWNLOAD_URL = f"{API_ENDPOINT}/download"

# IAM Authentication
def get_signed_request(url, method, body=None, headers=None):
    """Sign a request using IAM credentials from EC2 instance role"""
    if headers is None:
        headers = {}
    
    # Create a session using the EC2 instance role credentials
    session = boto3.Session()
    credentials = session.get_credentials()
    region = session.region_name or 'ap-south-1'
    
    # Create the request to sign
    request = AWSRequest(
        method=method,
        url=url,
        data=body,
        headers=headers
    )
    
    # Sign the request
    SigV4Auth(credentials, 'execute-api', region).add_auth(request)
    
    # Return the signed headers
    return dict(request.headers)

@app.route('/health')
def health_check():
    """Health check endpoint for load balancer"""
    return jsonify({'status': 'healthy'}), 200

@app.route('/')
def index():
    """Home page with file upload form"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file:
        # Get file data for size calculation
        file_data = file.read()
        file_size = len(file_data)
        filename = file.filename
        content_type = file.content_type or 'application/octet-stream'
        
        # Reset file pointer to beginning for later upload
        file.seek(0)
        
        # Prepare payload for Lambda function to get presigned URL
        payload = {
            'filename': filename,
            'content_type': content_type,
            'file_size': file_size
        }
        
        try:
            # Debug: Log API endpoint and payload size
            print(f"Sending request to: {UPLOAD_URL}")
            print(f"Payload size: {len(str(payload))} bytes")
            print(f"Filename: {filename}, Content-Type: {content_type}")
            
            try:
                # Send request to get presigned URL
                print(f"Sending request to: {UPLOAD_URL}")
                print(f"Payload: {payload}")
                
                # Prepare the request payload
                payload_json = json.dumps(payload)
                
                # Get signed headers for IAM authentication
                headers = get_signed_request(
                    url=UPLOAD_URL,
                    method='POST',
                    body=payload_json,
                    headers={'Content-Type': 'application/json'}
                )
                
                print(f"Using signed headers for IAM authentication")
                
                # Send request with signed headers
                response = requests.post(
                    UPLOAD_URL,
                    data=payload_json,
                    headers=headers
                )
                
                # Debug: Log response details
                print(f"Response status code: {response.status_code}")
                print(f"Response headers: {response.headers}")
                print(f"Response content: {response.text[:200]}...") # Show first 200 chars
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"Got presigned POST data: {result}")
                    
                    # Use the presigned POST data to upload the file directly to S3
                    upload_data = result.get('upload_data')
                    if not upload_data or 'url' not in upload_data or 'fields' not in upload_data:
                        flash('Failed to get upload data')
                        return redirect(url_for('index'))
                    
                    # Extract URL and fields from the presigned POST data
                    url = upload_data['url']
                    fields = upload_data['fields']
                    
                    # Prepare the POST request with fields and file
                    print(f"Uploading file to presigned POST URL: {url[:100]}...")
                    files = {'file': (filename, file_data, content_type)}
                    
                    # Upload file directly to S3 using the presigned POST
                    s3_response = requests.post(
                        url,
                        data=fields,
                        files={'file': (filename, file_data, content_type)}
                    )
                    
                    if s3_response.status_code in [200, 204]:
                        print(f"S3 upload successful: {s3_response.status_code}")
                        return render_template('success.html', result=result)
                    else:
                        error_message = f"S3 upload failed: {s3_response.status_code} - {s3_response.text[:100]}"
                        print(error_message)
                        flash(error_message)
                        return redirect(url_for('index'))
                else:
                    try:
                        error_data = response.json()
                        error_message = error_data.get('error', 'Unknown error')
                    except Exception as e:
                        error_message = f"Failed to parse error response: {str(e)}. Raw response: {response.text[:100]}"
                    
                    print(f"Error: {error_message}")
                    flash(f'Upload failed: {error_message}')
                    return redirect(url_for('index'))
                    
            except Exception as e:
                print(f"Exception during upload: {str(e)}")
                import traceback
                print(traceback.format_exc())
                flash(f'Error: {str(e)}')
                return redirect(url_for('index'))

        except Exception as e:
            print(f"Exception during upload: {str(e)}")
            import traceback
            print(traceback.format_exc())
            flash(f'Error: {str(e)}')
            return redirect(url_for('index'))

@app.route('/download/<file_id>')
def download_page(file_id):
    """Download page for shared files"""
    return render_template('download.html', file_id=file_id)

@app.route('/api/download/<file_id>')
def download_file(file_id):
    """Download a file using presigned URL"""
    try:
        # Get signed headers for IAM authentication
        headers = get_signed_request(
            url=f"{DOWNLOAD_URL}/{file_id}",
            method='GET',
            headers={'Content-Type': 'application/json'}
        )
        
        # Call Lambda function to get presigned download URL with IAM authentication
        response = requests.get(f"{DOWNLOAD_URL}/{file_id}", headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            download_url = result.get('download_url')
            
            if not download_url:
                return jsonify({'error': 'No download URL provided'}), 400
                
            # Redirect the user to the presigned URL for direct download
            # This is more efficient than proxying the file through our server
            return redirect(download_url)
        else:
            error_message = response.json().get('error', 'Unknown error')
            return jsonify({'error': error_message}), response.status_code
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check endpoint moved to line 48
# Removed duplicate route to fix deployment issue

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
