#!/usr/bin/env python3
"""
Test script to compare PDF text extraction methods.
This will help determine which method works best for your PDFs.
"""

import sys
import io
from pathlib import Path

def test_pypdf_extraction(pdf_path):
    """Test text extraction using PyPDF (current method)"""
    try:
        from pypdf import PdfReader
        
        with open(pdf_path, 'rb') as file:
            pdf_content = file.read()
        
        reader = PdfReader(io.BytesIO(pdf_content))
        text_content = []
        
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text.strip():
                    text_content.append(f"--- Page {page_num + 1} ---\n{page_text}")
            except Exception as e:
                print(f"PyPDF: Failed to extract text from page {page_num + 1}: {e}")
                continue
        
        extracted_text = "\n\n".join(text_content)
        return extracted_text
        
    except ImportError:
        return "PyPDF not installed. Install with: pip install pypdf"
    except Exception as e:
        return f"PyPDF extraction failed: {e}"

def test_pdfplumber_extraction(pdf_path):
    """Test text extraction using pdfplumber"""
    try:
        import pdfplumber
        
        text_content = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_content.append(f"--- Page {page_num + 1} ---\n{page_text}")
                except Exception as e:
                    print(f"pdfplumber: Failed to extract text from page {page_num + 1}: {e}")
                    continue
        
        extracted_text = "\n\n".join(text_content)
        return extracted_text
        
    except ImportError:
        return "pdfplumber not installed. Install with: pip install pdfplumber"
    except Exception as e:
        return f"pdfplumber extraction failed: {e}"

def test_pymupdf_extraction(pdf_path):
    """Test text extraction using PyMuPDF (fitz)"""
    try:
        import fitz  # PyMuPDF
        
        text_content = []
        
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            try:
                page = doc.load_page(page_num)
                page_text = page.get_text()
                if page_text and page_text.strip():
                    text_content.append(f"--- Page {page_num + 1} ---\n{page_text}")
            except Exception as e:
                print(f"PyMuPDF: Failed to extract text from page {page_num + 1}: {e}")
                continue
        
        doc.close()
        extracted_text = "\n\n".join(text_content)
        return extracted_text
        
    except ImportError:
        return "PyMuPDF not installed. Install with: pip install pymupdf"
    except Exception as e:
        return f"PyMuPDF extraction failed: {e}"

def test_pdfminer_extraction(pdf_path):
    """Test text extraction using pdfminer"""
    try:
        from pdfminer.high_level import extract_text
        
        extracted_text = extract_text(pdf_path)
        return extracted_text
        
    except ImportError:
        return "pdfminer not installed. Install with: pip install pdfminer.six"
    except Exception as e:
        return f"pdfminer extraction failed: {e}"

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_pdf_extraction.py <path_to_pdf>")
        print("Example: python test_pdf_extraction.py document.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"Error: File '{pdf_path}' not found")
        sys.exit(1)
    
    print(f"Testing PDF text extraction methods on: {pdf_path}")
    print("=" * 60)
    
    methods = [
        ("PyPDF (current method)", test_pypdf_extraction),
        ("pdfplumber", test_pdfplumber_extraction),
        ("PyMuPDF (fitz)", test_pymupdf_extraction),
        ("pdfminer", test_pdfminer_extraction),
    ]
    
    results = {}
    
    for method_name, method_func in methods:
        print(f"\n{method_name}:")
        print("-" * 40)
        
        result = method_func(pdf_path)
        results[method_name] = result
        
        if result.startswith(("not installed", "extraction failed")):
            print(f"❌ {result}")
        else:
            char_count = len(result.strip())
            if char_count > 0:
                print(f"✅ Extracted {char_count} characters")
                # Show first 200 characters as preview
                preview = result.strip()[:200]
                if len(result.strip()) > 200:
                    preview += "..."
                print(f"Preview: {preview}")
            else:
                print("❌ No text extracted")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("=" * 60)
    
    successful_methods = []
    for method_name, result in results.items():
        if not result.startswith(("not installed", "extraction failed")) and len(result.strip()) > 0:
            successful_methods.append((method_name, len(result.strip())))
    
    if successful_methods:
        print("✅ Methods that successfully extracted text:")
        for method, char_count in sorted(successful_methods, key=lambda x: x[1], reverse=True):
            print(f"  - {method}: {char_count} characters")
        
        best_method = max(successful_methods, key=lambda x: x[1])
        print(f"\n🏆 Best method: {best_method[0]} ({best_method[1]} characters)")
    else:
        print("❌ No methods successfully extracted text from this PDF")
        print("This PDF might be:")
        print("  - Image-only (scanned document)")
        print("  - Using complex text encoding")

if __name__ == "__main__":
    main()