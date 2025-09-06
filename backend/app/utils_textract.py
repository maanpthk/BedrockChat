"""
Textract utilities for OCR processing of scanned PDFs.
"""
import logging
import time
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def extract_text_with_textract(s3_bucket: str, s3_key: str, region: str = 'us-east-1') -> str:
    """
    Extract text from PDF using AWS Textract with LAYOUT feature.
    
    Args:
        s3_bucket: S3 bucket name
        s3_key: S3 key of the PDF file
        region: AWS region for Textract
    
    Returns:
        Formatted text content for LLM consumption
    """
    textract = boto3.client('textract', region_name=region)
    
    try:
        # Start async analysis for multi-page documents
        logger.info(f"Starting Textract analysis for s3://{s3_bucket}/{s3_key}")
        
        start_response = textract.start_document_analysis(
            DocumentLocation={
                'S3Object': {
                    'Bucket': s3_bucket,
                    'Name': s3_key
                }
            },
            FeatureTypes=['LAYOUT']
        )
        
        job_id = start_response['JobId']
        logger.info(f"Textract job started with ID: {job_id}")
        
        # Poll for completion
        max_wait_time = 300  # 5 minutes max
        poll_interval = 5    # Check every 5 seconds
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            response = textract.get_document_analysis(JobId=job_id)
            status = response['JobStatus']
            
            logger.info(f"Textract job status: {status} (elapsed: {elapsed_time}s)")
            
            if status == 'SUCCEEDED':
                logger.info("Textract job completed successfully!")
                
                # Get first batch of results (pagination not implemented for now)
                blocks = response.get('Blocks', [])
                total_pages = response.get('DocumentMetadata', {}).get('Pages', 0)
                
                logger.info(f"Processing {len(blocks)} blocks from {total_pages} pages")
                
                # Convert blocks to formatted text
                formatted_text = format_textract_blocks_for_llm(blocks)
                
                return formatted_text
                
            elif status == 'FAILED':
                error_msg = response.get('StatusMessage', 'Unknown error')
                raise Exception(f"Textract job failed: {error_msg}")
            
            elif status in ['IN_PROGRESS', 'PARTIAL_SUCCESS']:
                time.sleep(poll_interval)
                elapsed_time += poll_interval
            else:
                raise Exception(f"Unexpected Textract job status: {status}")
        
        raise Exception(f"Textract job timed out after {max_wait_time} seconds")
        
    except ClientError as e:
        logger.error(f"Textract error: {e}")
        raise Exception(f"Textract processing failed: {e}")


def format_textract_blocks_for_llm(blocks: List[Dict[str, Any]]) -> str:
    """
    Convert Textract blocks to LLM-friendly markdown text format.
    
    Args:
        blocks: List of Textract blocks
    
    Returns:
        Formatted text with markdown structure
    """
    # Organize blocks by type and ID
    blocks_by_type = {}
    blocks_by_id = {}
    
    for block in blocks:
        block_type = block.get('BlockType')
        block_id = block.get('Id')
        
        if block_type not in blocks_by_type:
            blocks_by_type[block_type] = []
        blocks_by_type[block_type].append(block)
        blocks_by_id[block_id] = block
    
    # Extract structured text
    structured_parts = []
    
    # Process pages in order
    pages = sorted(blocks_by_type.get('PAGE', []), key=lambda x: x.get('Page', 0))
    
    for page_block in pages:
        page_num = page_block.get('Page', 0)
        structured_parts.append(f"\n=== PAGE {page_num} ===\n")
        
        # Get relevant layout elements for this page
        layout_blocks = []
        
        # Add different layout block types
        for block_type in ['LAYOUT_TITLE', 'LAYOUT_HEADER', 'LAYOUT_SECTION_HEADER', 
                          'LAYOUT_TEXT', 'LAYOUT_LIST', 'LAYOUT_TABLE', 'LAYOUT_FOOTER']:
            page_blocks = [b for b in blocks_by_type.get(block_type, []) 
                          if b.get('Page') == page_num]
            layout_blocks.extend(page_blocks)
        
        # If no layout blocks, fall back to LINE blocks
        if not layout_blocks:
            line_blocks = [b for b in blocks_by_type.get('LINE', []) 
                          if b.get('Page') == page_num]
            layout_blocks = line_blocks
        
        # Sort by vertical position (top to bottom)
        layout_blocks.sort(key=lambda x: x.get('Geometry', {}).get('BoundingBox', {}).get('Top', 0))
        
        # Process each block
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
                elif block_type == 'LAYOUT_TABLE':
                    # Format table (simplified for now)
                    structured_parts.append(f"\n**Table:**\n{text.strip()}\n\n")
                else:  # LAYOUT_TEXT or LINE
                    structured_parts.append(f"{text.strip()}\n\n")
                
                # Add confidence warning for low-quality extractions
                if confidence < 80:
                    structured_parts.append(f"*[Low OCR confidence: {confidence:.1f}%]*\n")
    
    # Add tables if present
    table_blocks = blocks_by_type.get('TABLE', [])
    if table_blocks:
        structured_parts.append("\n## EXTRACTED TABLES\n")
        for table in table_blocks:
            table_text = extract_table_text(table, blocks_by_id)
            if table_text.strip():
                structured_parts.append(f"{table_text}\n\n")
    
    return ''.join(structured_parts)


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


def extract_table_text(table_block: Dict[str, Any], blocks_by_id: Dict[str, Any]) -> str:
    """
    Extract table content in markdown format.
    """
    # This is a simplified table extraction
    # For production, you'd want more sophisticated table parsing
    
    table_text = get_block_text(table_block, blocks_by_id)
    if table_text:
        return f"| Table Content |\n|---------------|\n| {table_text.replace(chr(10), ' | ')} |"
    
    return ""


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