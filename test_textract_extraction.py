#!/usr/bin/env python3
"""
Test script to extract text from PDF using AWS Textract with LAYOUT feature.
This will help us understand what data we'll be sending to the LLM.
"""

import boto3
import json
from pathlib import Path
from typing import Dict, List, Any
import argparse
import uuid
import time
from botocore.exceptions import ClientError


def validate_pdf_file(pdf_bytes: bytes) -> tuple[bool, dict]:
    """
    Validate that the file is a proper PDF and get basic info.
    """
    # Check PDF header
    if not pdf_bytes.startswith(b'%PDF-'):
        return False, {"error": "Not a valid PDF file"}
    
    # Check minimum size
    if len(pdf_bytes) < 1024:  # Less than 1KB is suspicious
        return False, {"error": "File too small"}
    
    # Try to estimate page count (rough heuristic)
    page_count_estimate = pdf_bytes.count(b'/Type/Page')
    
    return True, {
        "size_mb": len(pdf_bytes) / (1024*1024),
        "estimated_pages": page_count_estimate,
        "is_multipage": page_count_estimate > 1
    }


def extract_text_with_textract(pdf_path: str, bucket_name: str = "ab-anycomp-auth", 
                              force_s3: bool = False, force_direct: bool = False, region: str = 'us-east-1') -> Dict[str, Any]:
    """
    Extract text from PDF using AWS Textract with LAYOUT feature.
    
    Args:
        pdf_path: Path to the PDF file
        bucket_name: S3 bucket name for large files
    
    Returns:
        Dictionary containing extracted text and metadata
    """
    # Create clients with explicit region (Textract is not available in all regions)
    textract = boto3.client('textract', region_name=region)
    s3_client = boto3.client('s3')
    
    print(f"Textract region: {textract.meta.region_name}")
    print(f"S3 region: {s3_client.meta.region_name}")
    
    # Read and validate PDF file
    with open(pdf_path, 'rb') as file:
        pdf_bytes = file.read()
    
    is_valid, pdf_info = validate_pdf_file(pdf_bytes)
    if not is_valid:
        raise ValueError(f"Invalid PDF file: {pdf_path} - {pdf_info['error']}")
    
    file_size_mb = pdf_info["size_mb"]
    estimated_pages = pdf_info["estimated_pages"]
    is_multipage = pdf_info["is_multipage"]
    
    print(f"PDF size: {file_size_mb:.2f} MB")
    print(f"Estimated pages: {estimated_pages}")
    print(f"Multi-page: {is_multipage}")
    print(f"PDF validation: OK")
    
    # Determine processing method
    use_s3 = (file_size_mb > 5 or force_s3) and not force_direct
    use_async = is_multipage or file_size_mb > 5  # Multi-page PDFs need async API
    
    if use_async:
        print("Multi-page PDF detected - using asynchronous Textract API")
        return extract_with_async_textract(textract, s3_client, pdf_bytes, bucket_name, Path(pdf_path).name)
    elif use_s3:
        print("File size > 5MB, uploading to S3 first...")
        
        # Generate unique S3 key for temporary upload
        file_name = Path(pdf_path).name
        s3_key = f"textract-test/{uuid.uuid4()}_{file_name}"
        
        try:
            # Upload to S3 with proper metadata
            print(f"Uploading to s3://{bucket_name}/{s3_key}")
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=pdf_bytes,
                ContentType='application/pdf',
                Metadata={
                    'original-filename': file_name
                }
            )
            
            # Verify upload was successful
            print("Verifying S3 upload...")
            s3_client.head_object(Bucket=bucket_name, Key=s3_key)
            
            # Wait a moment for S3 consistency
            import time
            time.sleep(1)
            
            # Call Textract with S3 object
            print("Calling Textract with S3 object...")
            response = textract.analyze_document(
                Document={
                    'S3Object': {
                        'Bucket': bucket_name,
                        'Name': s3_key
                    }
                },
                FeatureTypes=['LAYOUT']  # Using LAYOUT to preserve document structure
            )
            
            # Clean up temporary S3 object
            print(f"Cleaning up temporary S3 object: {s3_key}")
            s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            print(f"AWS Error ({error_code}): {error_message}")
            
            # Print more details for debugging
            if error_code == 'UnsupportedDocumentException':
                print("Debugging info:")
                print(f"  - File size: {file_size_mb:.2f} MB")
                print(f"  - S3 bucket: {bucket_name}")
                print(f"  - S3 key: {s3_key}")
                print(f"  - Content type: application/pdf")
                print("  - Possible causes:")
                print("    1. PDF is corrupted or not a valid PDF")
                print("    2. PDF is encrypted or password protected")
                print("    3. PDF format is not supported by Textract")
                print("    4. S3 object permissions issue")
            
            # Try to clean up if upload succeeded but Textract failed
            try:
                print("Attempting cleanup...")
                s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
                print("Cleanup successful")
            except Exception as cleanup_error:
                print(f"Cleanup failed: {cleanup_error}")
            
            raise
        
    else:
        # Direct bytes upload for smaller files
        print("Using direct bytes upload...")
        
        # Try without LAYOUT first (basic text detection)
        try:
            print("Attempting basic text detection (no LAYOUT)...")
            response = textract.detect_document_text(
                Document={'Bytes': pdf_bytes}
            )
            print("Success with detect_document_text!")
            return response
        except ClientError as e:
            print(f"detect_document_text failed: {e}")
            print("Trying analyze_document with LAYOUT...")
            
        # If basic detection fails, try with LAYOUT
        response = textract.analyze_document(
            Document={'Bytes': pdf_bytes},
            FeatureTypes=['LAYOUT']  # Using LAYOUT to preserve document structure
        )
    
    return response


def extract_with_async_textract(textract_client, s3_client, pdf_bytes: bytes, 
                               bucket_name: str, filename: str) -> Dict[str, Any]:
    """
    Extract text using asynchronous Textract API for multi-page documents.
    """
    # Upload to S3 (required for async API)
    s3_key = f"textract-async/{uuid.uuid4()}_{filename}"
    
    try:
        print(f"Uploading to S3: s3://{bucket_name}/{s3_key}")
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=pdf_bytes,
            ContentType='application/pdf'
        )
        
        # Start async analysis
        print("Starting asynchronous Textract analysis...")
        start_response = textract_client.start_document_analysis(
            DocumentLocation={
                'S3Object': {
                    'Bucket': bucket_name,
                    'Name': s3_key
                }
            },
            FeatureTypes=['LAYOUT']
        )
        
        job_id = start_response['JobId']
        print(f"Job started with ID: {job_id}")
        
        # Poll for completion
        print("Waiting for job completion...")
        max_wait_time = 300  # 5 minutes max
        poll_interval = 5    # Check every 5 seconds
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            response = textract_client.get_document_analysis(JobId=job_id)
            status = response['JobStatus']
            
            print(f"Job status: {status} (elapsed: {elapsed_time}s)")
            
            if status == 'SUCCEEDED':
                print("Job completed successfully!")
                
                # For now, just return the first batch of results
                # We can add pagination later if needed for very large documents
                total_pages = response.get('DocumentMetadata', {}).get('Pages', 0)
                blocks_count = len(response.get('Blocks', []))
                has_more = 'NextToken' in response
                
                print(f"Document has {total_pages} pages, got {blocks_count} blocks")
                if has_more:
                    print("Note: This document has more results available (pagination not implemented)")
                
                # Return in same format as synchronous API
                return {
                    'DocumentMetadata': response.get('DocumentMetadata', {}),
                    'Blocks': response.get('Blocks', []),
                    'AnalyzeDocumentModelVersion': response.get('AnalyzeDocumentModelVersion', ''),
                    'JobId': job_id,  # Additional info for async
                    'HasMoreResults': has_more
                }
                
            elif status == 'FAILED':
                error_msg = response.get('StatusMessage', 'Unknown error')
                raise Exception(f"Textract job failed: {error_msg}")
            
            elif status in ['IN_PROGRESS', 'PARTIAL_SUCCESS']:
                time.sleep(poll_interval)
                elapsed_time += poll_interval
            else:
                raise Exception(f"Unexpected job status: {status}")
        
        raise Exception(f"Job timed out after {max_wait_time} seconds")
        
    finally:
        # Clean up S3 object
        try:
            print(f"Cleaning up S3 object: {s3_key}")
            s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
        except Exception as e:
            print(f"Failed to clean up S3 object: {e}")


def process_textract_blocks(textract_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process Textract response blocks into structured text for LLM consumption.
    
    Args:
        textract_response: Raw response from Textract
    
    Returns:
        Processed text data with structure preserved
    """
    blocks = textract_response.get('Blocks', [])
    
    # Organize blocks by type
    blocks_by_type = {}
    blocks_by_id = {}
    
    for block in blocks:
        block_type = block.get('BlockType')
        block_id = block.get('Id')
        
        if block_type not in blocks_by_type:
            blocks_by_type[block_type] = []
        blocks_by_type[block_type].append(block)
        blocks_by_id[block_id] = block
    
    # Extract text with layout structure
    structured_text = extract_structured_text(blocks_by_type, blocks_by_id)
    
    # Get metadata
    metadata = {
        'total_pages': textract_response.get('DocumentMetadata', {}).get('Pages', 0),
        'model_version': textract_response.get('AnalyzeDocumentModelVersion', ''),
        'block_counts': {block_type: len(blocks) for block_type, blocks in blocks_by_type.items()},
        'confidence_stats': calculate_confidence_stats(blocks)
    }
    
    return {
        'structured_text': structured_text,
        'raw_text': extract_raw_text(blocks_by_type),
        'metadata': metadata,
        'raw_response': textract_response  # For debugging
    }


def extract_structured_text(blocks_by_type: Dict[str, List], blocks_by_id: Dict[str, Any]) -> str:
    """
    Extract text while preserving document structure using LAYOUT blocks.
    """
    structured_parts = []
    
    # Process pages in order
    pages = sorted(blocks_by_type.get('PAGE', []), key=lambda x: x.get('Page', 0))
    
    for page_block in pages:
        page_num = page_block.get('Page', 0)
        structured_parts.append(f"\n=== PAGE {page_num} ===\n")
        
        # Get all layout elements for this page
        layout_blocks = [b for b in blocks_by_type.get('LAYOUT_TEXT', []) + 
                        blocks_by_type.get('LAYOUT_TITLE', []) + 
                        blocks_by_type.get('LAYOUT_HEADER', []) + 
                        blocks_by_type.get('LAYOUT_FOOTER', []) + 
                        blocks_by_type.get('LAYOUT_SECTION_HEADER', []) + 
                        blocks_by_type.get('LAYOUT_LIST', [])
                        if b.get('Page') == page_num]
        
        # Sort by vertical position (top to bottom)
        layout_blocks.sort(key=lambda x: x.get('Geometry', {}).get('BoundingBox', {}).get('Top', 0))
        
        for layout_block in layout_blocks:
            block_type = layout_block.get('BlockType', '')
            text = get_block_text(layout_block, blocks_by_id)
            confidence = layout_block.get('Confidence', 0)
            
            if text.strip():
                # Add structure markers based on block type
                if block_type == 'LAYOUT_TITLE':
                    structured_parts.append(f"\n# {text.strip()}\n")
                elif block_type == 'LAYOUT_HEADER':
                    structured_parts.append(f"\n## {text.strip()}\n")
                elif block_type == 'LAYOUT_SECTION_HEADER':
                    structured_parts.append(f"\n### {text.strip()}\n")
                elif block_type == 'LAYOUT_LIST':
                    # Format as list items
                    for line in text.strip().split('\n'):
                        if line.strip():
                            structured_parts.append(f"• {line.strip()}\n")
                elif block_type == 'LAYOUT_FOOTER':
                    structured_parts.append(f"\n---\n{text.strip()}\n---\n")
                else:  # LAYOUT_TEXT
                    structured_parts.append(f"{text.strip()}\n\n")
                
                # Add confidence info for low-confidence blocks
                if confidence < 80:
                    structured_parts.append(f"[Low confidence: {confidence:.1f}%]\n")
    
    return ''.join(structured_parts)


def extract_raw_text(blocks_by_type: Dict[str, List]) -> str:
    """
    Extract all text without structure (fallback method).
    """
    text_parts = []
    
    # Get all LINE blocks (contains the actual text)
    lines = blocks_by_type.get('LINE', [])
    
    # Sort by page, then by vertical position
    lines.sort(key=lambda x: (x.get('Page', 0), 
                             x.get('Geometry', {}).get('BoundingBox', {}).get('Top', 0)))
    
    current_page = 0
    for line in lines:
        page = line.get('Page', 0)
        if page != current_page:
            text_parts.append(f"\n=== PAGE {page} ===\n")
            current_page = page
        
        text = line.get('Text', '').strip()
        if text:
            text_parts.append(text + '\n')
    
    return ''.join(text_parts)


def get_block_text(block: Dict[str, Any], blocks_by_id: Dict[str, Any]) -> str:
    """
    Get text content from a block by following relationships.
    """
    # If block has direct text, return it
    if 'Text' in block:
        return block['Text']
    
    # Otherwise, follow CHILD relationships to get text
    text_parts = []
    relationships = block.get('Relationships', [])
    
    for relationship in relationships:
        if relationship.get('Type') == 'CHILD':
            child_ids = relationship.get('Ids', [])
            for child_id in child_ids:
                child_block = blocks_by_id.get(child_id)
                if child_block and child_block.get('BlockType') == 'LINE':
                    text = child_block.get('Text', '').strip()
                    if text:
                        text_parts.append(text)
    
    return '\n'.join(text_parts)


def calculate_confidence_stats(blocks: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate confidence statistics for the extraction.
    """
    confidences = [block.get('Confidence', 0) for block in blocks if 'Confidence' in block]
    
    if not confidences:
        return {}
    
    return {
        'min_confidence': min(confidences),
        'max_confidence': max(confidences),
        'avg_confidence': sum(confidences) / len(confidences),
        'low_confidence_blocks': len([c for c in confidences if c < 80])
    }


def main():
    parser = argparse.ArgumentParser(description='Test Textract extraction on a PDF file')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--output', '-o', help='Output file for results (JSON)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--bucket', '-b', default='ab-anycomp-auth', 
                       help='S3 bucket name for large files (default: ab-anycomp-auth)')
    parser.add_argument('--force-s3', action='store_true', 
                       help='Force S3 upload even for small files (for testing)')
    parser.add_argument('--force-direct', action='store_true', 
                       help='Force direct upload even for large files (will fail if >5MB)')
    parser.add_argument('--region', default='us-east-1',
                       help='AWS region for Textract (default: us-east-1)')
    
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        return 1
    
    try:
        print(f"Processing PDF: {pdf_path}")
        print("Calling AWS Textract...")
        
        # Extract text using Textract
        textract_response = extract_text_with_textract(
            str(pdf_path), 
            args.bucket, 
            force_s3=args.force_s3,
            force_direct=args.force_direct,
            region=args.region
        )
        
        print("Processing Textract response...")
        
        # Process the response
        processed_data = process_textract_blocks(textract_response)
        
        # Print results
        print("\n" + "="*80)
        print("EXTRACTION RESULTS")
        print("="*80)
        
        print(f"\nMetadata:")
        metadata = processed_data['metadata']
        print(f"  Pages: {metadata['total_pages']}")
        print(f"  Model Version: {metadata['model_version']}")
        print(f"  Block Counts: {metadata['block_counts']}")
        
        confidence_stats = metadata['confidence_stats']
        if confidence_stats:
            print(f"  Confidence Stats:")
            print(f"    Average: {confidence_stats['avg_confidence']:.1f}%")
            print(f"    Range: {confidence_stats['min_confidence']:.1f}% - {confidence_stats['max_confidence']:.1f}%")
            print(f"    Low confidence blocks: {confidence_stats['low_confidence_blocks']}")
        
        print(f"\n" + "-"*80)
        print("STRUCTURED TEXT (What we'll send to LLM):")
        print("-"*80)
        print(processed_data['structured_text'])
        
        if args.verbose:
            print(f"\n" + "-"*80)
            print("RAW TEXT (Fallback):")
            print("-"*80)
            print(processed_data['raw_text'])
        
        # Save to file if requested
        if args.output:
            output_data = {
                'pdf_path': str(pdf_path),
                'structured_text': processed_data['structured_text'],
                'raw_text': processed_data['raw_text'],
                'metadata': processed_data['metadata']
            }
            
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"\nResults saved to: {args.output}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())