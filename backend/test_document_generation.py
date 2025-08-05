#!/usr/bin/env python3
"""
Test script for document generation tools
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.agents.tools.document_generation import (
    PowerPointGenerationArgs,
    WordDocumentGenerationArgs,
    ExcelSpreadsheetGenerationArgs,
    generate_powerpoint,
    generate_word_document,
    generate_excel_spreadsheet,
)

def test_powerpoint_generation():
    """Test PowerPoint generation"""
    print("Testing PowerPoint generation...")
    
    args = PowerPointGenerationArgs(
        title="Sample Presentation",
        slides=[
            {
                "title": "Introduction",
                "content": "Welcome to our presentation about document generation tools."
            },
            {
                "title": "Key Features",
                "bullet_points": [
                    "Automatic PowerPoint generation",
                    "Customizable themes and colors",
                    "Multiple slide layouts",
                    "Professional formatting"
                ]
            },
            {
                "title": "Benefits",
                "bullet_points": [
                    "Save time on document creation",
                    "Consistent formatting",
                    "Easy to use",
                    "Integrates with chat interface"
                ]
            }
        ],
        theme_color="blue"
    )
    
    result = generate_powerpoint(args)
    print(f"PowerPoint generation result type: {type(result)}")
    if hasattr(result, 'name'):
        print(f"Generated file: {result.name}")
    print("✅ PowerPoint generation test completed\n")

def test_word_document_generation():
    """Test Word document generation"""
    print("Testing Word document generation...")
    
    args = WordDocumentGenerationArgs(
        title="Document Generation Guide",
        content=[
            {
                "type": "heading",
                "text": "Overview",
                "level": 1
            },
            {
                "type": "paragraph",
                "text": "This document demonstrates the capabilities of our automated document generation system. It can create professional documents with various formatting options."
            },
            {
                "type": "heading",
                "text": "Features",
                "level": 2
            },
            {
                "type": "bullet_list",
                "items": [
                    "Automatic heading generation",
                    "Paragraph formatting",
                    "Bullet and numbered lists",
                    "Professional styling"
                ]
            },
            {
                "type": "heading",
                "text": "Usage Examples",
                "level": 2
            },
            {
                "type": "numbered_list",
                "items": [
                    "Create reports and documentation",
                    "Generate meeting notes",
                    "Produce technical specifications",
                    "Build user manuals"
                ]
            }
        ],
        font_size=12
    )
    
    result = generate_word_document(args)
    print(f"Word document generation result type: {type(result)}")
    if hasattr(result, 'name'):
        print(f"Generated file: {result.name}")
    print("✅ Word document generation test completed\n")

def test_excel_spreadsheet_generation():
    """Test Excel spreadsheet generation"""
    print("Testing Excel spreadsheet generation...")
    
    args = ExcelSpreadsheetGenerationArgs(
        title="Sales Report",
        sheets=[
            {
                "name": "Q1 Sales",
                "headers": ["Product", "Units Sold", "Revenue", "Profit Margin"],
                "data": [
                    ["Product A", 150, 15000, "25%"],
                    ["Product B", 200, 30000, "30%"],
                    ["Product C", 100, 12000, "20%"],
                    ["Product D", 75, 9000, "15%"]
                ]
            },
            {
                "name": "Q2 Sales",
                "headers": ["Product", "Units Sold", "Revenue", "Profit Margin"],
                "data": [
                    ["Product A", 180, 18000, "25%"],
                    ["Product B", 220, 33000, "30%"],
                    ["Product C", 120, 14400, "20%"],
                    ["Product D", 90, 10800, "15%"]
                ]
            }
        ],
        include_charts=False
    )
    
    result = generate_excel_spreadsheet(args)
    print(f"Excel spreadsheet generation result type: {type(result)}")
    if hasattr(result, 'name'):
        print(f"Generated file: {result.name}")
    print("✅ Excel spreadsheet generation test completed\n")

if __name__ == "__main__":
    print("🚀 Starting document generation tests...\n")
    
    try:
        test_powerpoint_generation()
        test_word_document_generation()
        test_excel_spreadsheet_generation()
        
        print("🎉 All document generation tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()