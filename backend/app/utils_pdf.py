"""
PDF utilities for splitting large PDFs and handling file size constraints.
"""
import io
import logging
from typing import BinaryIO

from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)


def split_pdf_by_size(
    pdf_content: bytes, max_size_mb: float = 4.0
) -> list[tuple[bytes, int]]:
    """
    Split a PDF into chunks based on size limit.
    
    Args:
        pdf_content: PDF file content as bytes
        max_size_mb: Maximum size per chunk in MB
        
    Returns:
        List of tuples containing (pdf_chunk_bytes, page_count)
    """
    max_size_bytes = int(max_size_mb * 1024 * 1024)
    
    try:
        reader = PdfReader(io.BytesIO(pdf_content))
        total_pages = len(reader.pages)
        
        if total_pages == 0:
            logger.warning("PDF has no pages")
            return []
        
        chunks = []
        current_chunk = PdfWriter()
        current_pages = 0
        
        for i, page in enumerate(reader.pages):
            # Create a test writer with the current page added
            test_writer = PdfWriter()
            for existing_page_num in range(current_chunk.get_num_pages()):
                test_writer.add_page(current_chunk.pages[existing_page_num])
            test_writer.add_page(page)
            
            # Check size of test writer
            test_buffer = io.BytesIO()
            test_writer.write(test_buffer)
            test_size = test_buffer.tell()
            
            if test_size > max_size_bytes and current_chunk.get_num_pages() > 0:
                # Current chunk would exceed limit, finalize it
                chunk_buffer = io.BytesIO()
                current_chunk.write(chunk_buffer)
                chunks.append((chunk_buffer.getvalue(), current_pages))
                
                # Start new chunk with current page
                current_chunk = PdfWriter()
                current_chunk.add_page(page)
                current_pages = 1
            else:
                # Add page to current chunk
                current_chunk.add_page(page)
                current_pages += 1
        
        # Add final chunk if it has pages
        if current_chunk.get_num_pages() > 0:
            chunk_buffer = io.BytesIO()
            current_chunk.write(chunk_buffer)
            chunks.append((chunk_buffer.getvalue(), current_pages))
        
        logger.info(f"Split PDF into {len(chunks)} chunks from {total_pages} pages")
        return chunks
        
    except Exception as e:
        logger.error(f"Error splitting PDF: {e}")
        raise ValueError(f"Failed to split PDF: {str(e)}")


def get_pdf_info(pdf_content: bytes) -> dict:
    """
    Get basic information about a PDF.
    
    Args:
        pdf_content: PDF file content as bytes
        
    Returns:
        Dictionary with PDF info (page_count, size_mb)
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_content))
        return {
            "page_count": len(reader.pages),
            "size_mb": len(pdf_content) / (1024 * 1024),
        }
    except Exception as e:
        logger.error(f"Error reading PDF info: {e}")
        raise ValueError(f"Failed to read PDF: {str(e)}")