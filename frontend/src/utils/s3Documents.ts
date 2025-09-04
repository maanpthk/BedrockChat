/**
 * Utilities for handling S3 document uploads and downloads
 */

export interface DocumentUploadRequest {
  filename: string;
  content_type: string;
  file_size: number;
}

export interface DocumentUploadResponse {
  upload_url: string;
  s3_key: string;
  expires_in: number;
}

export interface DocumentDownloadResponse {
  download_url: string;
  expires_in: number;
}

export interface PDFSplitRequest {
  s3_key: string;
  max_size_mb?: number;
}

export interface PDFSplitResponse {
  chunks: Array<{
    chunk_index: number;
    s3_key: string;
    page_count: number;
    size_bytes: number;
    base64_content: string;
  }>;
  total_chunks: number;
}

/**
 * Get presigned URL for uploading a document
 */
export async function getDocumentUploadUrl(
  conversationId: string,
  uploadRequest: DocumentUploadRequest
): Promise<DocumentUploadResponse> {
  const response = await fetch(
    `/conversation/${conversationId}/documents/upload`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(uploadRequest),
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to get upload URL: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Upload file to S3 using presigned URL
 */
export async function uploadFileToS3(
  uploadUrl: string,
  file: File
): Promise<void> {
  const response = await fetch(uploadUrl, {
    method: 'PUT',
    body: file,
    headers: {
      'Content-Type': file.type,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to upload file: ${response.statusText}`);
  }
}

/**
 * Get presigned URL for downloading a document
 */
export async function getDocumentDownloadUrl(
  conversationId: string,
  s3Key: string
): Promise<DocumentDownloadResponse> {
  const encodedS3Key = encodeURIComponent(s3Key);
  const response = await fetch(
    `/conversation/${conversationId}/documents/${encodedS3Key}/download`
  );

  if (!response.ok) {
    throw new Error(`Failed to get download URL: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Split a PDF into smaller chunks
 */
export async function splitPDF(
  conversationId: string,
  splitRequest: PDFSplitRequest
): Promise<PDFSplitResponse> {
  const response = await fetch(
    `/conversation/${conversationId}/documents/split-pdf`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(splitRequest),
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to split PDF: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Check if a file should be stored in S3 based on size
 */
export function shouldUseS3Storage(fileSize: number): boolean {
  // Use S3 for files larger than 6MB (Lambda response limit)
  return fileSize > 4.5 * 1024 * 1024;
}

/**
 * Check if a PDF should be split based on size
 */
export function shouldSplitPDF(file: File): boolean {
  return file.type === 'application/pdf' && file.size > 4.5 * 1024 * 1024;
}