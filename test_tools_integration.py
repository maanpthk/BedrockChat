#!/usr/bin/env python3
"""
Simple test script to verify that tools are enabled for normal chat
"""

import sys
import os

# Add the backend app to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.agents.utils import get_tools

def test_tools_integration():
    """Test that tools are properly enabled for normal chat"""
    
    print("🧪 Testing Tools Integration for Normal Chat")
    print("=" * 50)
    
    # Test 1: Normal chat with tools enabled (bot = None)
    print("\n1. Testing normal chat with tools enabled (bot=None):")
    tools_normal_chat = get_tools(bot=None, enable_all_for_normal_chat=True)
    
    print(f"   Available tools: {len(tools_normal_chat)}")
    for tool_name in tools_normal_chat.keys():
        print(f"   ✅ {tool_name}")
    
    # Verify only document generation and Nova tools are included
    expected_tools = ['nova_canvas', 'nova_reel', 'excel_generator', 'word_generator', 'powerpoint_generator']
    excluded_tools = ['internet_search', 'bedrock_agent']
    
    print(f"\n   Expected tools for normal chat:")
    for tool in expected_tools:
        if tool in tools_normal_chat:
            print(f"   ✅ {tool} - Available")
        else:
            print(f"   ❌ {tool} - Missing")
    
    print(f"\n   Tools that should be excluded (bot-configurable only):")
    for tool in excluded_tools:
        if tool not in tools_normal_chat:
            print(f"   ✅ {tool} - Correctly excluded")
        else:
            print(f"   ❌ {tool} - Should be excluded")
    
    # Test 2: Normal chat with tools disabled (default behavior)
    print("\n2. Testing normal chat with tools disabled (default):")
    tools_disabled = get_tools(bot=None, enable_all_for_normal_chat=False)
    print(f"   Available tools: {len(tools_disabled)} (should be 0)")
    
    # Test 3: Verify knowledge tool is excluded for normal chat
    print("\n3. Verifying knowledge tool exclusion:")
    if 'knowledge_base_tool' not in tools_normal_chat:
        print("   ✅ knowledge_base_tool correctly excluded (requires bot context)")
    else:
        print("   ❌ knowledge_base_tool should be excluded for normal chat")
    
    print(f"\n🎉 Integration test completed!")
    print(f"   Normal chat tools: {len(tools_normal_chat)} available")
    print(f"   Nova Canvas: {'✅' if 'nova_canvas' in tools_normal_chat else '❌'}")
    print(f"   Nova Reel: {'✅' if 'nova_reel' in tools_normal_chat else '❌'}")

if __name__ == "__main__":
    try:
        test_tools_integration()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)