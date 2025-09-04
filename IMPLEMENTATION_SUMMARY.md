# Bedrock Chat S3 Document Implementation Summary

## Overview
This implementation adds S3 presigned URL flow for storing documents in conversations and PDF splitting functionality for files larger than 4.5MB, supporting up to 22MB files.

## Backend Changes

### 1. PDF Utilities (`backend/app/utils_pdf.py`)
- **`split_pdf_by_size()`**: Splits PDFs into chunks based on size limit (default 4.5MB)
- **`get_pdf_info()`**: Gets basic PDF information (page count, size)
- Uses `pypdf` library for PDF manipulation

### 2. S3 Document Utilities (`backend/app/utils_s3_documents.py`)
- **`get_document_presigned_upload_url()`**: Generates presigned URLs for uploading documents
- **`get_document_presigned_download_url()`**: Generates presigned URLs for downloading documents
- **`store_large_message_content()`**: Stores large message content in S3
- **`get_large_message_content()`**: Retrieves large message content from S3
- **`delete_large_message_content()`**: Deletes large message content from S3
- **`check_document_exists()`**: Checks if a document exists in S3

### 3. Updated Conversation Models
- Added `S3AttachmentContentModel` for S3-stored attachments
- Updated `ContentModel` union to include S3 attachments
- Added conversion methods between schemas and models

### 4. New API Schemas (`backend/app/routes/schemas/conversation.py`)
- **`S3AttachmentContent`**: Schema for S3-stored attachments
- **`DocumentUploadRequest/Response`**: Schemas for document upload flow
- **`DocumentDownloadResponse`**: Schema for document download flow
- **`PDFSplitRequest/Response`**: Schemas for PDF splitting

### 5. New API Endpoints (`backend/app/routes/conversation.py`)
- **`POST /conversation/{id}/documents/upload`**: Get presigned URL for uploading
- **`GET /conversation/{id}/documents/{s3_key}/download`**: Get presigned URL for downloading
- **`POST /conversation/{id}/documents/split-pdf`**: Split large PDFs into chunks

### 6. Updated Chat Logic (`backend/app/usecases/chat.py`)
- Added `resolve_s3_attachments_in_messages()` function
- S3 attachments are downloaded and converted to regular attachments before sending to Bedrock
- Updated chat flow to handle S3 attachment resolution

### 7. Dependencies
- Added `pypdf = "^5.1.0"` to `pyproject.toml`

## Frontend Changes

### 1. S3 Document Utilities (`frontend/src/utils/s3Documents.ts`)
- **`getDocumentUploadUrl()`**: Get presigned URL for uploading
- **`uploadFileToS3()`**: Upload file to S3 using presigned URL
- **`getDocumentDownloadUrl()`**: Get presigned URL for downloading
- **`splitPDF()`**: Split PDF into smaller chunks
- **`shouldUseS3Storage()`**: Check if file should use S3 storage
- **`shouldSplitPDF()`**: Check if PDF should be split

### 2. Updated Types
- Added `S3AttachmentType` to `useChat.ts`
- Added `S3AttachmentContent` to conversation types
- Updated `Content` union to include S3 attachments

### 3. Updated InputChatContent Component
- Added S3 attachment state management
- Updated file size limits:
  - `BEDROCK_MAX_FILE_SIZE_MB = 4.5` (Bedrock Converse API limit)
  - `MAX_SUPPORTED_FILE_SIZE_MB = 22` (Maximum supported file size)
  - `MAX_CONVERSATION_RESPONSE_MB = 6` (Lambda response limit)
- Added `handleLargeFileUpload()` for S3 uploads and PDF splitting
- Added display for S3 attached files
- Updated `onSend` to include S3 attachments

### 4. Updated Chat Components
- **ChatPage**: Updated to pass S3 attachments to `postChat`
- **ChatMessage**: Added display support for S3 attachments with download links
- **useChat**: Updated to handle S3 attachments in message content

## File Size Handling Strategy

### Small Files (< 6MB)
- Stored as base64 in message content (existing behavior)
- Sent directly to Bedrock Converse API

### Large Files (6MB - 22MB)
- Stored in S3 using presigned URLs
- Referenced in message content with S3 key
- Downloaded and converted to base64 before sending to Bedrock

### Large PDFs (> 4.5MB)
- Split into smaller chunks (each < 4.5MB)
- Each chunk stored as regular attachment
- Original file can be up to 22MB

## Environment Variables Required

### Backend
- `DOCUMENT_BUCKET`: S3 bucket for document storage
- `LARGE_MESSAGE_BUCKET`: S3 bucket for large message content

## Key Features

1. **Seamless File Handling**: Automatically determines whether to use S3 or inline storage
2. **PDF Splitting**: Large PDFs are automatically split into Bedrock-compatible chunks
3. **Presigned URLs**: Secure, time-limited access to S3 documents
4. **Backward Compatibility**: Existing small file handling remains unchanged
5. **Error Handling**: Graceful fallbacks and user feedback for upload/download failures

## Usage Flow

### Upload Large File
1. User selects file > 6MB
2. Frontend requests presigned upload URL
3. File uploaded directly to S3
4. S3 key stored in message content
5. Message sent with S3 reference

### Upload Large PDF
1. User selects PDF > 4.5MB
2. PDF uploaded to S3
3. Backend splits PDF into chunks
4. Each chunk added as regular attachment
5. Message sent with all chunks

### View S3 Document
1. User clicks on S3 attachment
2. Frontend requests presigned download URL
3. Document opens in new tab

### Send to Bedrock
1. Message with S3 attachments prepared
2. S3 attachments downloaded and converted to base64
3. Regular message sent to Bedrock Converse API

## Benefits

1. **Increased File Size Support**: Up to 22MB files (vs 6MB previously)
2. **Better Performance**: Large files don't impact Lambda response times
3. **Cost Optimization**: S3 storage is more cost-effective for large files
4. **Scalability**: Can handle many large files without memory issues
5. **User Experience**: Automatic PDF splitting for seamless Bedrock integration

## Testing

The implementation includes comprehensive error handling and should be tested with:
- Small files (< 6MB) - should work as before
- Large files (6-22MB) - should use S3 storage
- Large PDFs (> 4.5MB) - should be split automatically
- Very large files (> 22MB) - should show appropriate error message

## Security Considerations

1. **Presigned URLs**: Time-limited (1 hour) access to S3 objects
2. **Access Control**: Users can only access their own conversation documents
3. **S3 Key Structure**: Includes user ID and conversation ID for isolation
4. **File Validation**: File size and type validation on both frontend and backend