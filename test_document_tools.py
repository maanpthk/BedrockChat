#!/usr/bin/env python3
"""
Simple test script to verify document generation tools work correctly.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.agents.tools.document_generator import (
    excel_generator_tool,
    word_generator_tool,
    powerpoint_generator_tool,
    ExcelGeneratorInput,
    WordGeneratorInput,
    PowerPointGeneratorInput,
)

def test_excel_generation():
    """Test Excel generation tool."""
    print("Testing Excel generation...")
    
    # Sample data
    data = [
        {"Name": "John Doe", "Age": 30, "Department": "Engineering"},
        {"Name": "Jane Smith", "Age": 25, "Department": "Marketing"},
        {"Name": "Bob Johnson", "Age": 35, "Department": "Sales"}
    ]
    
    tool_input = ExcelGeneratorInput(
        title="Employee Report",
        data=data,
        sheet_name="Employees",
        include_header=True
    )
    
    try:
        result = excel_generator_tool.function(tool_input, None, None)
        print(f"✅ Excel generation successful: {result.name}")
        print(f"   Format: {result.format}")
        print(f"   Document size: {len(result.document)} bytes")
        return True
    except Exception as e:
        print(f"❌ Excel generation failed: {e}")
        return False

def test_word_generation():
    """Test Word generation tool."""
    print("Testing Word generation...")
    
    # Sample content
    content = [
        {"type": "heading", "text": "Introduction", "level": 2},
        {"type": "paragraph", "text": "This is a sample document generated using the document utility."},
        {"type": "list", "items": ["First item", "Second item", "Third item"]},
        {"type": "heading", "text": "Conclusion", "level": 2},
        {"type": "paragraph", "text": "Thank you for reading this document."}
    ]
    
    tool_input = WordGeneratorInput(
        title="Sample Report",
        content=content
    )
    
    try:
        result = word_generator_tool.function(tool_input, None, None)
        print(f"✅ Word generation successful: {result.name}")
        print(f"   Format: {result.format}")
        print(f"   Document size: {len(result.document)} bytes")
        return True
    except Exception as e:
        print(f"❌ Word generation failed: {e}")
        return False

def test_powerpoint_generation():
    """Test PowerPoint generation tool."""
    print("Testing PowerPoint generation...")
    
    # Sample slides
    slides = [
        {
            "title": "Welcome",
            "content": ["Introduction to our presentation", "Key topics we will cover"]
        },
        {
            "title": "Main Content",
            "content": ["First main point", "Second main point", "Supporting details"]
        },
        {
            "title": "Conclusion",
            "content": ["Summary of key points", "Next steps", "Thank you"]
        }
    ]
    
    tool_input = PowerPointGeneratorInput(
        title="Sample Presentation",
        slides=slides
    )
    
    try:
        result = powerpoint_generator_tool.function(tool_input, None, None)
        print(f"✅ PowerPoint generation successful: {result.name}")
        print(f"   Format: {result.format}")
        print(f"   Document size: {len(result.document)} bytes")
        return True
    except Exception as e:
        print(f"❌ PowerPoint generation failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Document Generation Tools\n")
    
    tests = [
        test_excel_generation,
        test_word_generation,
        test_powerpoint_generation,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())