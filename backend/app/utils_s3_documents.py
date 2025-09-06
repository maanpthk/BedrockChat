"""
S3 utilities for handling document storage with presigned URLs.
"""
import logging
import os
from typing import Optional
from uuid import uuid4

import boto3
from app.utils import generate_presigned_url
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Environment variables
DOCUMENT_BUCKET = os.environ.get("DOCUMENT_BUCKET", "")
LARGE_MESSAGE_BUCKET = os.environ.get("LARGE_MESSAGE_BUCKET", "")


def get_s3_bucket_name() -> str:
    """
    Get the S3 bucket name for documents.
    """
    if not DOCUMENT_BUCKET:
        raise ValueError("DOCUMENT_BUCKET environment variable not set")
    return DOCUMENT_BUCKET


def get_document_presigned_upload_url(
    user_id: str,
    conversation_id: str,
    filename: str,
    content_type: str,
    expiration: int = 3600,
) -> tuple[str, str]:
    """
    Generate presigned URL for uploading a document to S3.
    
    Args:
        user_id: User ID
        conversation_id: Conversation ID
        filename: Original filename
        content_type: MIME type of the file
        expiration: URL expiration time in seconds
        
    Returns:
        Tuple of (presigned_url, s3_key)
    """
    if not DOCUMENT_BUCKET:
        raise ValueError("DOCUMENT_BUCKET environment variable not set")
    
    # Generate unique S3 key
    file_id = str(uuid4())
    s3_key = f"conversations/{user_id}/{conversation_id}/documents/{file_id}_{filename}"
    
    presigned_url = generate_presigned_url(
        bucket=DOCUMENT_BUCKET,
        key=s3_key,
        content_type=content_type,
        expiration=expiration,
        client_method="put_object",
    )
    
    return presigned_url, s3_key


def get_document_presigned_download_url(
    s3_key: str,
    expiration: int = 3600,
) -> str:
    """
    Generate presigned URL for downloading a document from S3.
    
    Args:
        s3_key: S3 key of the document
        expiration: URL expiration time in seconds
        
    Returns:
        Presigned download URL
    """
    if not DOCUMENT_BUCKET:
        raise ValueError("DOCUMENT_BUCKET environment variable not set")
    
    return generate_presigned_url(
        bucket=DOCUMENT_BUCKET,
        key=s3_key,
        expiration=expiration,
        client_method="get_object",
    )


def store_large_message_content(
    user_id: str,
    conversation_id: str,
    message_id: str,
    content: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """
    Store large message content in S3 and return the S3 key.
    
    Args:
        user_id: User ID
        conversation_id: Conversation ID  
        message_id: Message ID
        content: Content to store
        content_type: MIME type of the content
        
    Returns:
        S3 key of the stored content
    """
    if not LARGE_MESSAGE_BUCKET:
        raise ValueError("LARGE_MESSAGE_BUCKET environment variable not set")
    
    s3_key = f"messages/{user_id}/{conversation_id}/{message_id}"
    
    client = boto3.client("s3")
    try:
        client.put_object(
            Bucket=LARGE_MESSAGE_BUCKET,
            Key=s3_key,
            Body=content,
            ContentType=content_type,
        )
        logger.info(f"Stored large message content at s3://{LARGE_MESSAGE_BUCKET}/{s3_key}")
        return s3_key
    except ClientError as e:
        logger.error(f"Failed to store large message content: {e}")
        raise


def get_large_message_content(s3_key: str) -> bytes:
    """
    Retrieve large message content from S3.
    
    Args:
        s3_key: S3 key of the content
        
    Returns:
        Content bytes
    """
    if not LARGE_MESSAGE_BUCKET:
        raise ValueError("LARGE_MESSAGE_BUCKET environment variable not set")
    
    client = boto3.client("s3")
    try:
        response = client.get_object(Bucket=LARGE_MESSAGE_BUCKET, Key=s3_key)
        return response["Body"].read()
    except ClientError as e:
        logger.error(f"Failed to retrieve large message content: {e}")
        raise


def delete_large_message_content(s3_key: str) -> None:
    """
    Delete large message content from S3.
    
    Args:
        s3_key: S3 key of the content to delete
    """
    if not LARGE_MESSAGE_BUCKET:
        raise ValueError("LARGE_MESSAGE_BUCKET environment variable not set")
    
    client = boto3.client("s3")
    try:
        client.delete_object(Bucket=LARGE_MESSAGE_BUCKET, Key=s3_key)
        logger.info(f"Deleted large message content at s3://{LARGE_MESSAGE_BUCKET}/{s3_key}")
    except ClientError as e:
        logger.error(f"Failed to delete large message content: {e}")
        # Don't raise - deletion failures shouldn't break the flow


def download_document_from_s3(s3_key: str) -> bytes:
    """
    Download document content directly from S3.
    
    Args:
        s3_key: S3 key of the document
        
    Returns:
        Document content as bytes
    """
    if not DOCUMENT_BUCKET:
        raise ValueError("DOCUMENT_BUCKET environment variable not set")
    
    client = boto3.client("s3")
    try:
        response = client.get_object(Bucket=DOCUMENT_BUCKET, Key=s3_key)
        content = response["Body"].read()
        
        # Debug: Log download details
        logger.info(f"Downloaded from S3: {s3_key}, size: {len(content)} bytes")
        if len(content) > 0:
            logger.info(f"Content starts with: {content[:20]}")
            if s3_key.endswith('.pdf') and not content.startswith(b'%PDF-'):
                logger.error(f"Downloaded content is not a valid PDF! First 50 bytes: {content[:50]}")
        else:
            logger.error(f"Downloaded empty content from S3 key: {s3_key}")
        
        return content
    except ClientError as e:
        logger.error(f"Failed to download document from S3: {e}")
        raise


def check_document_exists(s3_key: str) -> bool:
    """
    Check if a document exists in S3.
    
    Args:
        s3_key: S3 key to check
        
    Returns:
        True if document exists, False otherwise
    """
    if not DOCUMENT_BUCKET:
        return False
    
    client = boto3.client("s3")
    try:
        client.head_object(Bucket=DOCUMENT_BUCKET, Key=s3_key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise