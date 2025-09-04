/**
 * Utilities for handling S3 document uploads and downloads
 */
import { fetchAuthSession } from 'aws-amplify/auth';

// Get the API base URL from environment
const getApiBaseUrl = () => {
  return import.meta.env.VITE_APP_API_ENDPOINT || '';
};

// Helper function to get auth headers
const getAuthHeaders = async () => {
  const idToken = (await fetchAuthSession()).tokens?.idToken;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  if (idToken) {
    headers['Authorization'] = 'Bearer ' + idToken.toString();
  }
  
  return headers;
};

export interface DocumentUploadRequest {
  filename: string;
  content_type: string;
  file_size: number;
}

export interface DocumentUploadResponse {
  uploadUrl: string;
  s3Key: string;
  expiresIn: number;
}

export interface DocumentDownloadResponse {
  downloadUrl: string;
  expiresIn: number;
}

export interface PDFSplitRequest {
  s3_key: string;  // Keep snake_case for request body
  max_size_mb?: number;
}

export interface PDFSplitResponse {
  chunks: Array<{
    chunkIndex: number;
    s3Key: string;
    pageCount: number;
    sizeBytes: number;
    base64Content: string;
  }>;
  totalChunks: number;
}

/**
 * Get presigned URL for uploading a document
 */
export async function getDocumentUploadUrl(
  conversationId: string,
  uploadRequest: DocumentUploadRequest
): Promise<DocumentUploadResponse> {
  const baseUrl = getApiBaseUrl();
  const headers = await getAuthHeaders();
  
  const response = await fetch(
    `${baseUrl}/conversation/${conversationId}/documents/upload`,
    {
      method: 'POST',
      headers,
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
  const baseUrl = getApiBaseUrl();
  const headers = await getAuthHeaders();
  const encodedS3Key = encodeURIComponent(s3Key);
  
  const response = await fetch(
    `${baseUrl}/conversation/${conversationId}/documents/${encodedS3Key}/download`,
    {
      headers,
    }
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
  const baseUrl = getApiBaseUrl();
  const headers = await getAuthHeaders();
  
  const response = await fetch(
    `${baseUrl}/conversation/${conversationId}/documents/split-pdf`,
    {
      method: 'POST',
      headers,
      body: JSON.stringify(splitRequest),
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to split PDF: ${response.statusText}`);
  }

  return response.json();
}

import { 
  S3_STORAGE_THRESHOLD_BYTES, 
  MAX_FILE_SIZE_BYTES 
} from '../constants/supportedAttachedFiles';

/**
 * Check if a file should be stored in S3 based on size
 */
export function shouldUseS3Storage(fileSize: number): boolean {
  // Use S3 for files larger than the storage threshold
  return fileSize > S3_STORAGE_THRESHOLD_BYTES;
}

/**
 * Check if a PDF should be split based on size
 */
export function shouldSplitPDF(file: File): boolean {
  return file.type === 'application/pdf' && file.size > MAX_FILE_SIZE_BYTES;
}