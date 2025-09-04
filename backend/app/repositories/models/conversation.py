from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal, Self, TypeGuard
from urllib.parse import urlparse

from app.repositories.common import decompose_conv_id
from app.repositories.models.common import Base64EncodedBytes
from app.routes.schemas.conversation import (
    AttachmentContent,
    Content,
    DocumentToolResult,
    ImageContent,
    ImageToolResult,
    JsonToolResult,
    MessageInput,
    ReasoningContent,
    RelatedDocument,
    S3AttachmentContent,
    SimpleMessage,
    TextContent,
    TextToolResult,
    ToolResult,
    ToolResultContent,
    ToolResultContentBody,
    ToolUseContent,
    ToolUseContentBody,
    type_model_name,
)
from app.utils import generate_presigned_url
from mypy_boto3_bedrock_runtime.literals import DocumentFormatType, ImageFormatType
from mypy_boto3_bedrock_runtime.type_defs import (
    ContentBlockTypeDef,
    ToolResultBlockTypeDef,
    ToolResultContentBlockOutputTypeDef,
    ToolUseBlockOutputTypeDef,
    ToolUseBlockTypeDef,
)
from pydantic import BaseModel, Discriminator, Field, JsonValue, field_validator

if TYPE_CHECKING:
    from app.agents.tools.agent_tool import ToolRunResult

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TextContentModel(BaseModel):
    content_type: Literal["text"]
    body: str = Field(
        ...,
        description="Text string.",
    )

    @classmethod
    def from_text_content(cls, content: TextContent) -> Self:
        return cls(
            content_type="text",
            body=content.body,
        )

    def to_content(self) -> Content:
        return TextContent(
            content_type="text",
            body=self.body,
        )

    def to_contents_for_converse(self) -> list[ContentBlockTypeDef]:
        return [
            {
                "text": self.body,
            }
        ]


def _is_converse_supported_image_format(format: str) -> TypeGuard[ImageFormatType]:
    return format in {"gif", "jpeg", "png", "webp"}


class ImageContentModel(BaseModel):
    content_type: Literal["image"]
    media_type: str
    body: Base64EncodedBytes = Field(
        ...,
        description="Image bytes.",
    )

    @classmethod
    def from_image_content(cls, content: ImageContent) -> Self:
        return cls(
            content_type="image",
            media_type=content.media_type,
            body=content.body,
        )

    def to_content(self) -> Content:
        return ImageContent(
            content_type="image",
            media_type=self.media_type,
            body=self.body,
        )

    def to_contents_for_converse(self) -> list[ContentBlockTypeDef]:
        # e.g. "image/png" -> "png"
        format = self.media_type.split("/")[1] if self.media_type else "unknown"

        return (
            [
                {
                    "image": {
                        "format": format,
                        "source": {"bytes": self.body},
                    },
                },
            ]
            if _is_converse_supported_image_format(format)
            else []
        )


def _is_converse_supported_document_format(ext: str) -> TypeGuard[DocumentFormatType]:
    supported_formats = {
        "pdf",
        "csv",
        "doc",
        "docx",
        "xls",
        "xlsx",
        "html",
        "txt",
        "md",
    }
    return ext in supported_formats


def _convert_to_valid_file_name(file_name: str) -> str:
    # Note: The document file name can only contain alphanumeric characters,
    # whitespace characters, hyphens, parentheses, and square brackets.
    # The name can't contain more than one consecutive whitespace character.
    file_name = re.sub(r"[^a-zA-Z0-9\s\-\(\)\[\]]", "", file_name)
    file_name = re.sub(r"\s+", " ", file_name)
    file_name = file_name.strip()

    return file_name


class AttachmentContentModel(BaseModel):
    content_type: Literal["attachment"]
    body: Base64EncodedBytes = Field(
        ...,
        description="Attachment file bytes.",
    )
    file_name: str

    @classmethod
    def from_attachment_content(cls, content: AttachmentContent) -> Self:
        return cls(
            content_type="attachment",
            body=content.body,
            file_name=content.file_name,
        )

    def to_content(self) -> Content:
        return AttachmentContent(
            content_type="attachment",
            body=self.body,
            file_name=self.file_name,
        )

    def to_contents_for_converse(self) -> list[ContentBlockTypeDef]:
        import logging
        logger = logging.getLogger(__name__)
        
        # e.g. "document.txt" -> "txt"
        format = Path(self.file_name).suffix[1:]

        # e.g. "document.txt" -> "document"
        name = Path(self.file_name).stem

        if _is_converse_supported_document_format(format):
            logger.info(f"Converting attachment to Bedrock format: {self.file_name}, format: {format}, body size: {len(self.body)} bytes")
            
            # Debug: Check the type and content of self.body
            logger.info(f"Body type: {type(self.body)}, Body length: {len(self.body)}")
            if len(self.body) > 0:
                logger.info(f"First 20 bytes: {self.body[:20]}")
                # Verify it's a valid PDF
                if format == "pdf" and not self.body.startswith(b'%PDF-'):
                    logger.error(f"Invalid PDF: does not start with PDF header!")
                    logger.error(f"Actual start: {self.body[:50]}")
            else:
                logger.error(f"Document {self.file_name} has empty body!")
            
            # For PDF chunks, create more descriptive names and add context
            document_name = _convert_to_valid_file_name(name)
            context = None
            
            if format == "pdf" and ("part" in name.lower() or "chunk" in name.lower()):
                # This is a PDF chunk - add context to help Bedrock understand
                if "part_1" in name or "chunk_1" in name:
                    context = "This is part 1 of a multi-part PDF document"
                elif "part_2" in name or "chunk_2" in name:
                    context = "This is part 2 of a multi-part PDF document"
                elif "part_3" in name or "chunk_3" in name:
                    context = "This is part 3 of a multi-part PDF document"
                elif "part_4" in name or "chunk_4" in name:
                    context = "This is part 4 of a multi-part PDF document"
                else:
                    context = "This is part of a multi-part PDF document"
                
                # Make the name more descriptive
                if "_part_" in name:
                    base_name = name.split("_part_")[0]
                    part_num = name.split("_part_")[1]
                    document_name = f"Document Part {part_num}"
                elif "_chunk_" in name:
                    base_name = name.split("_chunk_")[0]
                    chunk_num = name.split("_chunk_")[1]
                    document_name = f"Document Chunk {chunk_num}"
            
            # Debug: Check the type and content of self.body
            logger.info(f"Body type: {type(self.body)}, Body length: {len(self.body)}")
            if len(self.body) > 0:
                logger.info(f"First 20 bytes: {self.body[:20]}")
                # Verify it's a valid PDF
                if format == "pdf" and not self.body.startswith(b'%PDF-'):
                    logger.error(f"Invalid PDF: does not start with PDF header!")
                    logger.error(f"Actual start: {self.body[:50]}")
            
            document_block = {
                "document": {
                    "format": format,
                    "name": document_name,
                    "source": {"bytes": self.body},
                }
            }
            
            if context:
                document_block["document"]["context"] = context
            
            return [document_block]
        else:
            logger.warning(f"Unsupported document format for Bedrock: {format} (file: {self.file_name})")
            return []


class S3AttachmentContentModel(BaseModel):
    content_type: Literal["s3_attachment"]
    file_name: str
    s3_key: str
    file_size: int
    mime_type: str

    @classmethod
    def from_s3_attachment_content(cls, content: S3AttachmentContent) -> Self:
        return cls(
            content_type="s3_attachment",
            file_name=content.file_name,
            s3_key=content.s3_key,
            file_size=content.file_size,
            mime_type=content.mime_type,
        )

    def to_content(self) -> Content:
        return S3AttachmentContent(
            content_type="s3_attachment",
            file_name=self.file_name,
            s3_key=self.s3_key,
            file_size=self.file_size,
            mime_type=self.mime_type,
        )

    def to_contents_for_converse(self) -> list[ContentBlockTypeDef]:
        # S3 attachments need to be downloaded and converted to regular attachments
        # This should be handled by the caller before sending to Bedrock
        logger.warning(f"S3 attachment {self.file_name} needs to be resolved before sending to Bedrock")
        return []


class FeedbackModel(BaseModel):
    thumbs_up: bool
    category: str
    comment: str


class ChunkModel(BaseModel):
    content: str
    content_type: str = Field(default="s3")
    source: str
    rank: int


class ToolUseContentModelBody(BaseModel):
    tool_use_id: str
    name: str
    input: dict[str, JsonValue]

    @classmethod
    def from_tool_use_content(cls, tool_use_content: ToolUseBlockOutputTypeDef) -> Self:
        return cls(
            tool_use_id=tool_use_content["toolUseId"],
            name=tool_use_content["name"],
            input=tool_use_content["input"],
        )

    @classmethod
    def from_tool_use_content_body(cls, body: ToolUseContentBody) -> Self:
        return cls(
            tool_use_id=body.tool_use_id,
            name=body.name,
            input=body.input,
        )

    def to_tool_use_content_body(self) -> ToolUseContentBody:
        return ToolUseContentBody(
            tool_use_id=self.tool_use_id,
            name=self.name,
            input=self.input,
        )

    def to_tool_use_for_converse(self) -> ToolUseBlockTypeDef:
        return {
            "toolUseId": self.tool_use_id,
            "name": self.name,
            "input": self.input,
        }


class ToolUseContentModel(BaseModel):
    content_type: Literal["toolUse"] = Field(
        ..., description="Content type. Note that image is only available for claude 3."
    )
    body: ToolUseContentModelBody

    @classmethod
    def from_tool_use_content(cls, content: ToolUseContent) -> Self:
        return cls(
            content_type="toolUse",
            body=ToolUseContentModelBody.from_tool_use_content_body(body=content.body),
        )

    def to_content(self) -> Content:
        return ToolUseContent(
            content_type="toolUse",
            body=self.body.to_tool_use_content_body(),
        )

    def to_contents_for_converse(self) -> list[ContentBlockTypeDef]:
        return [
            {
                "toolUse": self.body.to_tool_use_for_converse(),
            },
        ]


class TextToolResultModel(BaseModel):
    text: str

    @classmethod
    def from_text_tool_result(cls, tool_result: TextToolResult) -> Self:
        return cls(
            text=tool_result.text,
        )

    def to_tool_result(self) -> ToolResult:
        return TextToolResult(
            text=self.text,
        )

    def to_content_for_converse(self) -> ToolResultContentBlockOutputTypeDef:
        return {
            "text": self.text,
        }


class JsonToolResultModel(BaseModel):
    json_: dict[str, JsonValue] = Field(
        alias="json"
    )  # `json` is a reserved keyword on pydantic

    @classmethod
    def from_json_tool_result(cls, tool_result: JsonToolResult) -> Self:
        return cls(
            json=tool_result.json_,
        )

    def to_tool_result(self) -> ToolResult:
        return JsonToolResult(
            json=self.json_,
        )

    def to_content_for_converse(self) -> ToolResultContentBlockOutputTypeDef:
        return {
            "json": self.json_,
        }


class ImageToolResultModel(BaseModel):
    format: ImageFormatType
    image: Base64EncodedBytes

    @classmethod
    def from_image_tool_result(cls, tool_result: ImageToolResult) -> Self:
        return cls(
            format=tool_result.format,
            image=tool_result.image,
        )

    def to_tool_result(self) -> ToolResult:
        return ImageToolResult(
            format=self.format,
            image=self.image,
        )

    def to_content_for_converse(self) -> ToolResultContentBlockOutputTypeDef:
        return {
            "image": {
                "format": self.format,
                "source": {
                    "bytes": self.image,
                },
            },
        }


class DocumentToolResultModel(BaseModel):
    format: DocumentFormatType
    name: str
    document: Base64EncodedBytes

    @classmethod
    def from_document_tool_result(cls, tool_result: DocumentToolResult) -> Self:
        return cls(
            format=tool_result.format,
            name=tool_result.name,
            document=tool_result.document,
        )

    def to_tool_result(self) -> ToolResult:
        return DocumentToolResult(
            format=self.format,
            name=self.name,
            document=self.document,
        )

    def to_content_for_converse(self) -> ToolResultContentBlockOutputTypeDef:
        return {
            "document": {
                "format": self.format,
                "name": self.name,
                "source": {
                    "bytes": self.document,
                },
            },
        }


ToolResultModel = (
    TextToolResultModel
    | JsonToolResultModel
    | ImageToolResultModel
    | DocumentToolResultModel
)


def tool_result_model_from_tool_result(tool_result: ToolResult) -> ToolResultModel:
    if isinstance(tool_result, TextToolResult):
        return TextToolResultModel.from_text_tool_result(tool_result=tool_result)

    elif isinstance(tool_result, JsonToolResult):
        return JsonToolResultModel.from_json_tool_result(tool_result=tool_result)

    elif isinstance(tool_result, ImageToolResult):
        return ImageToolResultModel.from_image_tool_result(tool_result=tool_result)

    elif isinstance(tool_result, DocumentToolResult):
        return DocumentToolResultModel.from_document_tool_result(
            tool_result=tool_result
        )

    else:
        raise ValueError(f"Unknown tool result type")


def tool_result_model_from_tool_result_content(
    content: ToolResultContentBlockOutputTypeDef,
) -> ToolResultModel:
    if "text" in content:
        return TextToolResultModel(text=content["text"])

    elif "json" in content:
        return JsonToolResultModel(json=content["json"])

    elif "image" in content:
        return ImageToolResultModel(
            format=content["image"]["format"],
            image=(
                content["image"]["source"]["bytes"]
                if "bytes" in content["image"]["source"]
                else b""
            ),
        )

    elif "document" in content:
        return DocumentToolResultModel(
            format=content["document"]["format"],
            name=content["document"]["name"],
            document=(
                content["document"]["source"]["bytes"]
                if "bytes" in content["document"]["source"]
                else b""
            ),
        )

    else:
        raise ValueError(f"Unknown tool result type")


class ToolResultContentModelBody(BaseModel):
    tool_use_id: str
    content: list[ToolResultModel]
    status: Literal["error", "success"]

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v: Any) -> list:
        if type(v) == list:
            return v

        else:
            # For backward compatibility
            return [v]

    @classmethod
    def from_tool_result_content_body(cls, body: ToolResultContentBody) -> Self:
        return cls(
            tool_use_id=body.tool_use_id,
            content=[
                tool_result_model_from_tool_result(tool_result=tool_result)
                for tool_result in body.content
            ],
            status=body.status,
        )

    def to_tool_result_for_converse(self) -> ToolResultBlockTypeDef:
        return {
            "toolUseId": self.tool_use_id,
            "status": self.status,
            "content": [content.to_content_for_converse() for content in self.content],
        }

    def to_tool_result_content_body(self) -> ToolResultContentBody:
        return ToolResultContentBody(
            tool_use_id=self.tool_use_id,
            content=[content.to_tool_result() for content in self.content],
            status=self.status,
        )


class ToolResultContentModel(BaseModel):
    content_type: Literal["toolResult"] = Field(
        ..., description="Content type. Note that image is only available for claude 3."
    )
    body: ToolResultContentModelBody

    @classmethod
    def from_tool_result_content(cls, content: ToolResultContent) -> Self:
        return cls(
            content_type="toolResult",
            body=ToolResultContentModelBody.from_tool_result_content_body(content.body),
        )

    @classmethod
    def from_tool_run_result(
        cls,
        run_result: ToolRunResult,
        model: type_model_name,
        display_citation: bool,
    ) -> Self:
        result_contents = [
            related_document.to_tool_result_model(
                display_citation=display_citation,
            )
            for related_document in run_result["related_documents"]
        ]

        from app.bedrock import is_nova_model

        if is_nova_model(model=model):
            text_or_json_contents = [
                result_content
                for result_content in result_contents
                if isinstance(result_content, TextToolResultModel)
                or isinstance(result_content, JsonToolResultModel)
            ]
            if len(text_or_json_contents) > 1:
                return cls(
                    content_type="toolResult",
                    body=ToolResultContentModelBody(
                        tool_use_id=run_result["tool_use_id"],
                        content=[
                            TextToolResultModel(
                                text=json.dumps(
                                    [
                                        (
                                            content.json_
                                            if isinstance(content, JsonToolResultModel)
                                            else content.text
                                        )
                                        for content in text_or_json_contents
                                    ]
                                ),
                            ),
                        ],
                        status=run_result["status"],
                    ),
                )

        return cls(
            content_type="toolResult",
            body=ToolResultContentModelBody(
                tool_use_id=run_result["tool_use_id"],
                content=result_contents,
                status=run_result["status"],
            ),
        )

    def to_content(self) -> Content:
        return ToolResultContent(
            content_type="toolResult",
            body=self.body.to_tool_result_content_body(),
        )

    def to_contents_for_converse(self) -> list[ContentBlockTypeDef]:
        return [
            {
                "toolResult": self.body.to_tool_result_for_converse(),
            },
        ]


class ReasoningContentModel(BaseModel):
    content_type: Literal["reasoning"]
    text: str
    signature: str
    redacted_content: Base64EncodedBytes

    def to_content(self) -> Content:
        return ReasoningContent(
            content_type="reasoning",
            text=self.text,
            signature=self.signature,
            redacted_content=self.redacted_content,
        )

    def to_contents_for_converse(self) -> list[ContentBlockTypeDef]:
        # Ref: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/converse.html
        # Ref: https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking

        if self.text:
            return [
                {
                    "reasoningContent": {  # type: ignore
                        "reasoningText": {
                            "text": self.text,
                            "signature": self.signature,
                        },
                    }
                }
            ]
        else:
            return [
                {
                    "reasoningContent": {  # type: ignore
                        "redactedContent": {"data": self.redacted_content},
                    }
                }
            ]


ContentModel = Annotated[
    TextContentModel
    | ImageContentModel
    | AttachmentContentModel
    | S3AttachmentContentModel
    | ToolUseContentModel
    | ToolResultContentModel
    | ReasoningContentModel,
    Discriminator("content_type"),
]


def content_model_from_content(content: Content) -> ContentModel:

    if isinstance(content, TextContent):
        return TextContentModel.from_text_content(content=content)

    elif isinstance(content, ImageContent):
        return ImageContentModel.from_image_content(content=content)

    elif isinstance(content, AttachmentContent):
        return AttachmentContentModel.from_attachment_content(content=content)

    elif isinstance(content, S3AttachmentContent):
        return S3AttachmentContentModel.from_s3_attachment_content(content=content)

    elif isinstance(content, ToolUseContent):
        return ToolUseContentModel.from_tool_use_content(content=content)

    elif isinstance(content, ToolResultContent):
        return ToolResultContentModel.from_tool_result_content(content=content)
    else:
        raise ValueError(f"Unknown content type")


class SimpleMessageModel(BaseModel):
    role: str
    content: list[ContentModel]

    @classmethod
    def from_message_model(cls, message: MessageModel):
        return SimpleMessageModel(
            role=message.role,
            content=message.content,
        )

    def to_schema(self) -> SimpleMessage:
        return SimpleMessage(
            role=self.role,
            content=[content.to_content() for content in self.content],
        )


class MessageModel(BaseModel):
    role: str
    content: list[ContentModel]
    model: type_model_name
    children: list[str]
    parent: str | None
    create_time: float
    feedback: FeedbackModel | None = None
    used_chunks: list[ChunkModel] | None = None
    thinking_log: list[SimpleMessageModel] | None = Field(
        default=None, description="Only available for agent."
    )

    @field_validator("thinking_log", mode="before")
    @classmethod
    def validate_thinking_log(cls, v: Any) -> list | None:
        if type(v) == list:
            return v

        else:
            # For backward compatibility
            return None

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v: Any) -> list:
        if type(v) == list:
            return v

        else:
            # For backward compatibility
            return [v]

    @classmethod
    def from_message_input(cls, message_input: MessageInput):
        return MessageModel(
            role=message_input.role,
            content=[
                content_model_from_content(content=content)
                for content in message_input.content
            ],
            model=message_input.model,
            children=[],
            parent=message_input.parent_message_id,
            create_time=0,
            feedback=None,
            used_chunks=None,
            thinking_log=None,
        )


class ConversationModel(BaseModel):
    id: str
    create_time: float
    title: str
    total_price: float
    message_map: dict[str, MessageModel]
    last_message_id: str
    bot_id: str | None
    should_continue: bool


class ConversationMeta(BaseModel):
    id: str
    title: str
    create_time: float
    model: str
    bot_id: str | None


class RelatedDocumentModel(BaseModel):
    content: ToolResultModel
    source_id: str
    source_name: str | None = None
    source_link: str | None = None
    page_number: int | None = None

    def to_tool_result_model(self, display_citation: bool) -> ToolResultModel:
        if isinstance(self.content, TextToolResultModel):
            if display_citation:
                json_result = {
                    "source_id": self.source_id,
                    "content": self.content.text,
                }
                # Include source_link if available
                if self.source_link:
                    json_result["source_link"] = self.source_link
                return JsonToolResultModel(json=json_result)

            else:
                return self.content

        elif isinstance(self.content, JsonToolResultModel):
            if display_citation:
                json_result = {
                    "source_id": self.source_id,
                    "content": self.content.json_,
                }
                # Include source_link if available
                if self.source_link:
                    json_result["source_link"] = self.source_link
                return JsonToolResultModel(json=json_result)

            else:
                return self.content

        else:
            return self.content

    def get_source_link_for_schema(self) -> str | None:
        if self.source_link is None:
            return None

        url = urlparse(url=self.source_link)
        if url.scheme == "s3":
            # Handle S3 URLs by generating presigned URLs
            source_link = generate_presigned_url(
                bucket=url.netloc,
                key=url.path.removeprefix("/"),
                client_method="get_object",
            )
            return source_link
        elif url.scheme in ["http", "https"]:
            # Return HTTPS URLs as-is (already presigned URLs from document generator)
            return self.source_link
        else:
            # Return the source as is for knowledge base references or other schemes
            return self.source_link

    def to_schema(self) -> RelatedDocument:
        return RelatedDocument(
            content=self.content.to_tool_result(),
            source_id=self.source_id,
            source_name=self.source_name,
            source_link=self.get_source_link_for_schema(),
            page_number=self.page_number,
        )
