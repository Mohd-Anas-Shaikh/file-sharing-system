# File Sharing System (AWS)

A web application for temporary file sharing that automatically expires files after 24 hours. Built with Python, Flask, AWS Lambda, and S3.

## Features

- Upload files and generate shareable links
- Download shared files via unique links
- Automatic file expiration after 24 hours
- Clean, responsive user interface
- Secure file storage using AWS S3
- Serverless architecture with AWS Lambda

## Architecture

- **Frontend**: Flask web application
- **Backend**: AWS Lambda functions (Python)
- **Storage**: AWS S3
- **File Expiration**: Scheduled Lambda function + S3 lifecycle policies

## Project Structure

```
file-sharing-system-aws/
├── backend/
│   ├── lambda/
│   │   ├── upload/
│   │   │   └── lambda_function.py
│   │   ├── download/
│   │   │   └── lambda_function.py
│   │   └── cleanup/
│   │       └── lambda_function.py
│   └── requirements.txt
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── success.html
│   │   └── download.html
│   ├── app.py
│   └── requirements.txt
├── scripts/
│   └── setup_aws_resources.py
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- AWS account with appropriate permissions
- AWS CLI installed and configured

### AWS Resources Setup

1. Configure AWS CLI if not already done:
   ```
   aws configure
   ```

2. Run the setup script to create all necessary AWS resources:
   ```
   cd file-sharing-system-aws
   python scripts/setup_aws_resources.py
   ```

   This script will:
   - Create an S3 bucket for file storage
   - Set up S3 lifecycle policies for automatic expiration
   - Create IAM roles and policies for Lambda functions
   - Deploy Lambda functions for upload, download, and cleanup
   - Create API Gateway endpoints
   - Configure environment variables

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd file-sharing-system-aws/frontend
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the Flask application:
   ```
   python app.py
   ```

## Usage

1. **Uploading Files**:
   - Visit the home page
   - Select a file to upload (max 6MB due to Lambda payload limits)
   - Click "Upload File"
   - Copy the generated shareable link

2. **Downloading Files**:
   - Open the shareable link
   - Click "Download File"
   - The file will be downloaded to your device

3. **File Expiration**:
   - Files automatically expire after 24 hours
   - Expired files are automatically deleted from S3
   - Links to expired files will show an error message

## Deployment

### AWS Lambda Functions

The Lambda functions are deployed automatically by the setup script. To update them:

```
cd file-sharing-system-aws
python scripts/setup_aws_resources.py
```

### Frontend

The frontend can be deployed to any Python web hosting service like AWS Elastic Beanstalk:

1. Create an Elastic Beanstalk environment:
   ```
   eb init -p python-3.8 file-sharing-system
   eb create file-sharing-env
   ```

2. Deploy the application:
   ```
   eb deploy
   ```

## Security Considerations

- Files are stored in a private S3 bucket
- Direct access to S3 objects is not allowed
- Files are accessed only through authenticated Lambda functions
- Files are automatically deleted after 24 hours
- API Gateway endpoints use CORS protection

## Limitations

- Maximum file size is limited to 6MB due to Lambda payload limits
- No user authentication system (anyone with the link can download the file)
- No encryption for stored files (could be added as an enhancement)

## Future Enhancements

- Add user authentication
- Implement file encryption
- Support for larger file uploads using S3 presigned URLs
- Custom expiration times
- Password protection for shared links

## License

This project is licensed under the MIT License.
