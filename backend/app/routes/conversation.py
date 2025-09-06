import logging
import os
import uuid

from app.repositories.conversation import (
    change_conversation_title,
    delete_conversation_by_id,
    delete_conversation_by_user_id,
    find_conversation_by_user_id,
    find_related_document_by_id,
    find_related_documents_by_conversation_id,
    update_feedback,
)
from app.repositories.models.conversation import FeedbackModel
from app.routes.schemas.conversation import (
    ChatInput,
    ChatOutput,
    Conversation,
    ConversationMetaOutput,
    ConversationSearchResult,
    DocumentDownloadResponse,
    DocumentUploadRequest,
    DocumentUploadResponse,
    FeedbackInput,
    FeedbackOutput,
    NewTitleInput,
    PDFChunkInfo,
    PDFSplitRequest,
    PDFSplitResponse,
    ProposedTitle,
    RelatedDocument,
)
from app.usecases.chat import (
    chat,
    chat_output_from_message,
    fetch_conversation,
    propose_conversation_title,
    search_conversations as search_conversations_usecase,
)
from app.user import User
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["conversation"])

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@router.get("/health")
def health():
    """For health check"""
    return {"status": "ok"}


@router.post("/conversation", response_model=ChatOutput)
def post_message(request: Request, chat_input: ChatInput):
    """Send chat message"""
    current_user: User = request.state.current_user

    conversation, message = chat(user=current_user, chat_input=chat_input)
    output = chat_output_from_message(conversation=conversation, message=message)
    return output


@router.get(
    "/conversation/{conversation_id}/related-documents",
    response_model=list[RelatedDocument],
)
def get_related_documents(
    request: Request, conversation_id: str
) -> list[RelatedDocument]:
    """Get related documents"""
    current_user: User = request.state.current_user

    related_documents = find_related_documents_by_conversation_id(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )
    return [related_document.to_schema() for related_document in related_documents]


@router.get(
    "/conversation/{conversation_id}/related-documents/{source_id}",
    response_model=RelatedDocument,
)
def get_related_document(
    request: Request, conversation_id: str, source_id: str
) -> RelatedDocument:
    """Get a related document"""
    current_user: User = request.state.current_user

    related_document = find_related_document_by_id(
        user_id=current_user.id,
        conversation_id=conversation_id,
        source_id=source_id,
    )
    return related_document.to_schema()


@router.get("/conversation/{conversation_id}", response_model=Conversation)
def get_conversation(request: Request, conversation_id: str):
    """Get a conversation history"""
    current_user: User = request.state.current_user

    output = fetch_conversation(current_user.id, conversation_id)
    return output


@router.delete("/conversation/{conversation_id}")
def remove_conversation(request: Request, conversation_id: str):
    """Delete conversation"""
    current_user: User = request.state.current_user

    delete_conversation_by_id(current_user.id, conversation_id)


@router.get("/conversations", response_model=list[ConversationMetaOutput])
def get_all_conversations(
    request: Request,
):
    """Get all conversation metadata"""
    current_user: User = request.state.current_user

    conversations = find_conversation_by_user_id(current_user.id)
    output = [
        ConversationMetaOutput(
            id=conversation.id,
            title=conversation.title,
            create_time=conversation.create_time,
            model=conversation.model,
            bot_id=conversation.bot_id,
        )
        for conversation in conversations
    ]
    return output


@router.delete("/conversations")
def remove_all_conversations(request: Request):
    """Delete all conversations"""
    delete_conversation_by_user_id(request.state.current_user.id)


@router.get("/conversations/search", response_model=list[ConversationSearchResult])
def search_conversations(request: Request, query: str):
    """Search conversations by keyword"""
    current_user: User = request.state.current_user
    output = search_conversations_usecase(query, current_user)
    return output


@router.patch("/conversation/{conversation_id}/title")
def patch_conversation_title(
    request: Request, conversation_id: str, new_title_input: NewTitleInput
):
    """Update conversation title"""
    current_user: User = request.state.current_user

    change_conversation_title(
        current_user.id, conversation_id, new_title_input.new_title
    )


@router.get(
    "/conversation/{conversation_id}/proposed-title", response_model=ProposedTitle
)
def get_proposed_title(request: Request, conversation_id: str):
    """Suggest conversation title"""
    current_user: User = request.state.current_user

    title = propose_conversation_title(current_user.id, conversation_id)
    return ProposedTitle(title=title)


@router.put(
    "/conversation/{conversation_id}/{message_id}/feedback",
    response_model=FeedbackOutput,
)
def put_feedback(
    request: Request,
    conversation_id: str,
    message_id: str,
    feedback_input: FeedbackInput,
):
    """Send feedback."""
    current_user: User = request.state.current_user

    update_feedback(
        user_id=current_user.id,
        conversation_id=conversation_id,
        message_id=message_id,
        feedback=FeedbackModel(
            thumbs_up=feedback_input.thumbs_up,
            category=feedback_input.category if feedback_input.category else "",
            comment=feedback_input.comment if feedback_input.comment else "",
        ),
    )
    return FeedbackOutput(
        thumbs_up=feedback_input.thumbs_up,
        category=feedback_input.category if feedback_input.category else "",
        comment=feedback_input.comment if feedback_input.comment else "",
    )


@router.post("/conversation/{conversation_id}/documents/upload", response_model=DocumentUploadResponse)
def get_document_upload_url(
    request: Request, 
    conversation_id: str, 
    upload_request: DocumentUploadRequest
):
    """Get presigned URL for uploading a document"""
    from app.utils_s3_documents import get_document_presigned_upload_url
    
    current_user: User = request.state.current_user
    
    upload_url, s3_key = get_document_presigned_upload_url(
        user_id=current_user.id,
        conversation_id=conversation_id,
        filename=upload_request.filename,
        content_type=upload_request.content_type,
    )
    
    return DocumentUploadResponse(
        upload_url=upload_url,
        s3_key=s3_key,
        expires_in=3600,
    )


@router.get("/conversation/{conversation_id}/documents/{s3_key:path}/download", response_model=DocumentDownloadResponse)
def get_document_download_url(
    request: Request,
    conversation_id: str,
    s3_key: str,
):
    """Get presigned URL for downloading a document"""
    from app.utils_s3_documents import get_document_presigned_download_url, check_document_exists
    
    current_user: User = request.state.current_user
    
    # Verify the document exists and belongs to the user
    valid_prefixes = [
        f"conversations/{current_user.id}/{conversation_id}/documents/",
        f"conversations/{current_user.id}/temp/documents/"
    ]
    if not any(s3_key.startswith(prefix) for prefix in valid_prefixes):
        raise HTTPException(
            status_code=403,
            detail="Access denied to this document"
        )
    
    if not check_document_exists(s3_key):
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )
    
    download_url = get_document_presigned_download_url(s3_key)
    
    return DocumentDownloadResponse(
        download_url=download_url,
        expires_in=3600,
    )


@router.post("/conversation/{conversation_id}/documents/split-pdf", response_model=PDFSplitResponse)
def split_pdf_document(
    request: Request,
    conversation_id: str,
    split_request: PDFSplitRequest,
):
    """Split a large PDF into smaller chunks"""
    import base64
    from app.utils_pdf import split_pdf_by_size
    from app.utils_s3_documents import get_large_message_content, store_large_message_content
    
    current_user: User = request.state.current_user
    
    # Verify the document belongs to the user
    valid_prefixes = [
        f"conversations/{current_user.id}/{conversation_id}/documents/",
        f"conversations/{current_user.id}/temp/documents/"
    ]
    if not any(split_request.s3_key.startswith(prefix) for prefix in valid_prefixes):
        raise HTTPException(
            status_code=403,
            detail="Access denied to this document"
        )
    
    try:
        # Get the PDF content from S3 document bucket
        import boto3
        from botocore.exceptions import ClientError
        
        if not os.environ.get("DOCUMENT_BUCKET"):
            raise HTTPException(status_code=500, detail="Document bucket not configured")
            
        s3_client = boto3.client("s3")
        try:
            response = s3_client.get_object(Bucket=os.environ["DOCUMENT_BUCKET"], Key=split_request.s3_key)
            pdf_content = response["Body"].read()
        except ClientError as e:
            logger.error(f"Failed to download document from S3: {split_request.s3_key}, error: {e}")
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Split the PDF
        chunks = split_pdf_by_size(pdf_content, split_request.max_size_mb)
        
        # Store each chunk and create response
        chunk_info = []
        for i, (chunk_bytes, page_count) in enumerate(chunks):
            # Debug: Validate chunk content
            logger.info(f"Chunk {i}: {len(chunk_bytes)} bytes, pages: {page_count}")
            if len(chunk_bytes) > 0:
                logger.info(f"Chunk {i} starts with: {chunk_bytes[:20]}")
                if not chunk_bytes.startswith(b'%PDF-'):
                    logger.error(f"Chunk {i} is not a valid PDF!")
                else:
                    # Try to validate the PDF chunk by reading it
                    try:
                        from app.utils_pdf import get_pdf_info, extract_text_from_pdf
                        chunk_info_test = get_pdf_info(chunk_bytes)
                        logger.info(f"Chunk {i} validation: {chunk_info_test}")
                        
                        # Check if the PDF has extractable text
                        try:
                            text_content = extract_text_from_pdf(chunk_bytes)
                            if text_content.strip():
                                logger.info(f"Chunk {i} has {len(text_content)} characters of extractable text")
                            else:
                                logger.warning(f"Chunk {i} has no extractable text - might be image-only PDF")
                        except Exception as text_e:
                            logger.error(f"Chunk {i} text extraction failed: {text_e}")
                    except Exception as e:
                        logger.error(f"Chunk {i} PDF validation failed: {e}")
            else:
                logger.error(f"Chunk {i} is empty!")
            
            # Store chunk in S3 document bucket (same as original files)
            import uuid
            chunk_file_id = str(uuid.uuid4())
            original_filename = split_request.s3_key.split('/')[-1]
            chunk_filename = f"{chunk_file_id}_{original_filename.rsplit('.', 1)[0]}_chunk_{i}.pdf"
            
            # Use same path structure as document uploads
            chunk_s3_key = f"conversations/{current_user.id}/{conversation_id}/documents/{chunk_filename}"
            
            # Store chunk directly in document bucket
            s3_client.put_object(
                Bucket=os.environ["DOCUMENT_BUCKET"],
                Key=chunk_s3_key,
                Body=chunk_bytes,
                ContentType="application/pdf"
            )
            
            logger.info(f"Stored chunk {i} to S3: {chunk_s3_key}")
            
            logger.info(f"Stored chunk {i} to S3: {chunk_s3_key}")
            
            # Generate presigned download URL for the chunk
            from app.utils_s3_documents import get_document_presigned_download_url
            chunk_download_url = get_document_presigned_download_url(chunk_s3_key)
            
            # Generate chunk file name
            original_filename = split_request.s3_key.split('/')[-1]
            chunk_filename = f"{original_filename.rsplit('.', 1)[0]}_part_{i+1}.pdf"
            
            chunk_info.append(PDFChunkInfo(
                chunk_index=i,
                s3_key=chunk_s3_key,
                page_count=page_count,
                size_bytes=len(chunk_bytes),
                download_url=chunk_download_url,
                file_name=chunk_filename,
            ))
        
        return PDFSplitResponse(
            chunks=chunk_info,
            total_chunks=len(chunks),
        )
        
    except Exception as e:
        logger.error(f"Error splitting PDF: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to split PDF: {str(e)}"
        )