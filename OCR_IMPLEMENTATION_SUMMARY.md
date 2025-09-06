# OCR Implementation Summary

## Overview
Implemented OCR processing for scanned PDFs using AWS Textract with minimal frontend changes and smart backend routing.

## Frontend Changes

### 1. **Scanned Images Marker**
- Added checkbox: "Contains scanned images" 
- Appears when PDFs are present in upload queue
- Stored in Zustand state: `containsScannedImages`

### 2. **Upload Logic Updates**
- **No splitting** when `containsScannedImages` is true
- **OCR flag** added to S3 attachments: `requiresOCR: boolean`
- **Type updates** across frontend (useChat.ts, InputChatContent.tsx)

### 3. **UI Behavior**
- Checkbox only shows when PDFs are uploaded
- Disabled during loading states
- Persists across file uploads in same session

## Backend Changes

### 1. **Schema Updates**
- **S3AttachmentContent**: Added `requires_ocr: bool = False`
- **S3AttachmentContentModel**: Added OCR flag handling
- **Backward compatible**: Existing attachments work unchanged

### 2. **New Textract Utility** (`utils_textract.py`)
- **Asynchronous processing**: Uses `StartDocumentAnalysis` + `GetDocumentAnalysis`
- **Markdown formatting**: Converts Textract blocks to LLM-friendly text
- **Structure preservation**: Headers, paragraphs, tables, lists
- **Error handling**: Timeouts, job failures, cleanup

### 3. **Chat Processing Updates**
- **Smart routing** in `resolve_s3_attachments_in_messages()`
- **OCR path**: PDF → Textract → Text content → LLM
- **Regular path**: PDF → Binary → LLM (unchanged)
- **Fallback**: OCR failure → skip attachment (graceful degradation)

## Processing Flow

```
User Upload → Check "Scanned Images" → Upload Decision
     ↓              ↓                      ↓
   Store S3    OCR Required?         Split/No Split
     ↓              ↓                      ↓
Chat Request → Route Decision → Textract/Binary Processing
     ↓              ↓                      ↓
   LLM Call ← Text Content ← Formatted Markdown
```

## Key Features

### 1. **Textract Integration**
- **Multi-page support**: Handles documents up to 3000 pages
- **Layout preservation**: Maintains document structure
- **Block filtering**: Uses LINE, LAYOUT_*, TABLE blocks (skips WORD noise)
- **Confidence tracking**: Warns about low-quality extractions

### 2. **LLM-Optimized Output**
```markdown
=== PAGE 1 ===

# Document Title

## Section Header

Regular paragraph text with proper formatting.

### Subsection

• List item 1
• List item 2

**Table:**
| Column 1 | Column 2 |
|----------|----------|
| Data     | Data     |

*[Low OCR confidence: 75.2%]*
```

### 3. **Error Handling**
- **Graceful fallbacks**: OCR failure → skip attachment
- **Timeout protection**: 5-minute max processing time
- **Validation**: PDF header checks, content validation
- **Logging**: Comprehensive error tracking

### 4. **Cost Optimization**
- **User-controlled**: Only process when explicitly requested
- **No unnecessary splitting**: Scanned PDFs bypass 4MB chunking
- **Efficient text**: Extracted text is always <4MB (no Lambda limits)

## Usage

### Frontend
```typescript
// User checks "Contains scanned images" checkbox
// Upload proceeds without splitting
// OCR flag is set on S3 attachment
```

### Backend
```python
# Chat processing automatically detects OCR flag
if content.requires_ocr and content.file_name.endswith('.pdf'):
    extracted_text = extract_text_with_textract(bucket, s3_key)
    # Send formatted text to LLM instead of binary PDF
```

## Benefits

1. **Better LLM Understanding**: Structured text vs binary PDF
2. **No Size Limits**: Text extraction eliminates 4MB/6MB constraints  
3. **User Control**: Explicit opt-in for OCR processing
4. **Cost Efficient**: Only process when needed
5. **Backward Compatible**: Existing PDFs work unchanged
6. **Graceful Degradation**: Failures don't break chat functionality

## Next Steps

1. **Test with sample scanned PDFs**
2. **Monitor Textract costs and performance**
3. **Add pagination support** for very large documents (if needed)
4. **Implement caching** for repeated OCR requests
5. **Add confidence thresholds** and user feedback mechanisms

## Files Modified

### Frontend
- `frontend/src/components/InputChatContent.tsx`
- `frontend/src/hooks/useChat.ts`

### Backend  
- `backend/app/routes/schemas/conversation.py`
- `backend/app/repositories/models/conversation.py`
- `backend/app/usecases/chat.py`
- `backend/app/utils_s3_documents.py`
- `backend/app/utils_textract.py` (new)

The implementation is now ready for testing with scanned PDFs!