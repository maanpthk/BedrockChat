# File Upload Logic Cleanup Summary

## Changes Made to InputChatContent.tsx

### 1. Removed Unused Constants
- Removed `S3_STORAGE_THRESHOLD_BYTES` and `S3_STORAGE_THRESHOLD_MB` imports (no longer needed)
- Removed local `BEDROCK_MAX_FILE_SIZE_MB` and `BEDROCK_MAX_FILE_SIZE_BYTES` constants (using imports instead)
- Removed `MAX_CONVERSATION_RESPONSE_BYTES` constant (no longer needed)

### 2. Removed Regular File Upload Logic
- **Completely removed** `handleRegularFileUpload` function since all files now go to S3
- This eliminates the base64 encoding path that was causing Lambda response size issues

### 3. Updated File Processing Logic
- All files now use `handleLargeFileUpload()` regardless of size
- Simplified the logic in `handleAttachedFileRead()` to always use S3 storage
- Removed the `shouldUseS3` decision logic

### 4. Updated Dependency Arrays
- Fixed `handleAttachedFileRead` dependencies: `[handleLargeFileUpload, open, t]`
- Fixed `handleLargeFileUpload` dependencies: `[pushS3File, open, t, props.conversationId]`

### 5. Updated File Count Logic
- Updated file count validation to include both regular and S3 attached files
- This ensures the total file limit is respected across both storage types

## Current Behavior
- **All files** (regardless of size) are uploaded to S3
- **No 6MB total limit** - users can upload many files
- **PDFs >4MB** are automatically split into chunks
- **No Lambda response size issues** - everything uses S3 references
- **Backward compatibility** maintained for existing regular attachments

## Files Still Supporting Regular Attachments
The component still supports displaying and sending regular attachments for backward compatibility, but the upload path no longer creates them. All new uploads go through S3.

## Next Steps
The implementation is now ready for testing. The 6MB Lambda response limit issue should be resolved since all file content now goes through S3 instead of being embedded in the response.