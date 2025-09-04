import logging
from typing import Callable, Dict

from app.agents.tools.agent_tool import AgentTool, ToolRunResult
from app.agents.tools.knowledge import create_knowledge_tool
from app.agents.utils import get_tools
from app.bedrock import (
    call_converse_api,
    compose_args_for_converse_api,
    is_tooluse_supported,
)
from app.prompt import build_rag_prompt, get_prompt_to_cite_tool_results
from app.repositories.conversation import (
    RecordNotFoundError,
    find_conversation_by_id,
    store_conversation,
    store_related_documents,
)
from app.repositories.conversation_search import find_conversations_by_query
from app.repositories.custom_bot import alias_exists, store_alias
from app.repositories.models.conversation import (
    AttachmentContentModel,
    ConversationModel,
    MessageModel,
    ReasoningContentModel,
    RelatedDocumentModel,
    S3AttachmentContentModel,
    SimpleMessageModel,
    TextContentModel,
    ToolResultContentModel,
    ToolUseContentModel,
)
from app.repositories.models.custom_bot import (
    BotAliasModel,
    BotModel,
    ConversationQuickStarterModel,
    GenerationParamsModel,
)
from app.routes.schemas.conversation import (
    ChatInput,
    ChatOutput,
    Chunk,
    Conversation,
    ConversationMetaOutput,
    ConversationSearchResult,
    FeedbackOutput,
    MessageOutput,
    SearchHighlight,
    type_model_name,
)
from app.stream import ConverseApiStreamHandler, OnStopInput, OnThinking
from app.usecases.bot import fetch_bot, modify_bot_last_used_time, modify_bot_stats
from app.user import User
from app.utils import get_current_time
from app.vector_search import (
    SearchResult,
    search_related_docs,
    search_result_to_related_document,
    to_guardrails_grounding_source,
)
from ulid import ULID

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def prepare_conversation(
    user: User,
    chat_input: ChatInput,
) -> tuple[str, ConversationModel, BotModel | None]:
    current_time = get_current_time()
    bot = None

    try:
        # Fetch existing conversation
        conversation = find_conversation_by_id(user.id, chat_input.conversation_id)
        logger.info(f"Found conversation: {conversation}")
        parent_id = chat_input.message.parent_message_id
        if chat_input.message.parent_message_id == "system" and chat_input.bot_id:
            # The case editing first user message and use bot
            parent_id = "instruction"
        elif chat_input.message.parent_message_id is None:
            parent_id = conversation.last_message_id
        if chat_input.bot_id:
            logger.info("Bot id is provided. Fetching bot.")
            owned, bot = fetch_bot(user, chat_input.bot_id)
    except RecordNotFoundError:
        # The case for new conversation. Note that editing first user message is not considered as new conversation.
        logger.info(
            f"No conversation found with id: {chat_input.conversation_id}. Creating new conversation."
        )

        initial_message_map = {
            # Dummy system message, which is used for root node of the message tree.
            "system": MessageModel(
                role="system",
                content=[
                    TextContentModel(
                        content_type="text",
                        body="",
                    )
                ],
                model=chat_input.message.model,
                children=[],
                parent=None,
                create_time=current_time,
                feedback=None,
                used_chunks=None,
                thinking_log=None,
            )
        }
        parent_id = "system"
        if chat_input.bot_id:
            logger.info("Bot id is provided. Fetching bot.")
            parent_id = "instruction"
            # Fetch bot and append instruction
            owned, bot = fetch_bot(user, chat_input.bot_id)
            initial_message_map["instruction"] = MessageModel(
                role="instruction",
                content=[
                    TextContentModel(
                        content_type="text",
                        body=bot.instruction,
                    )
                ],
                model=chat_input.message.model,
                children=[],
                parent="system",
                create_time=current_time,
                feedback=None,
                used_chunks=None,
                thinking_log=None,
            )
            initial_message_map["system"].children.append("instruction")

            if not owned:
                try:
                    # Check alias is already created
                    alias_exists(user.id, chat_input.bot_id)
                except RecordNotFoundError:
                    logger.info(
                        "Bot is not owned by the user. Creating alias to shared bot."
                    )
                    # Create alias item
                    store_alias(user.id, BotAliasModel.from_bot_for_initial_alias(bot))

        # Create new conversation
        conversation = ConversationModel(
            id=chat_input.conversation_id,
            title="New conversation",
            total_price=0.0,
            create_time=current_time,
            message_map=initial_message_map,
            last_message_id="",
            bot_id=chat_input.bot_id,
            should_continue=False,
        )

    # Append user chat input to the conversation
    if not chat_input.continue_generate:
        new_message = MessageModel.from_message_input(chat_input.message)
        new_message.parent = parent_id
        new_message.create_time = current_time

        if chat_input.message.message_id:
            message_id = chat_input.message.message_id
        else:
            message_id = str(ULID())

        conversation.message_map[message_id] = new_message
        conversation.message_map[parent_id].children.append(message_id)  # type: ignore

    # If the "Generate continue" button is pressed, a new_message is not generated.
    else:
        message_id = (
            conversation.message_map[conversation.last_message_id].parent
            or "instruction"
        )

    return (message_id, conversation, bot)


def trace_to_root(
    node_id: str | None, message_map: dict[str, MessageModel]
) -> list[SimpleMessageModel]:
    """Trace message map from leaf node to root node."""
    result: list[SimpleMessageModel] = []
    if not node_id or node_id == "system":
        node_id = "instruction" if "instruction" in message_map else "system"

    current_node = message_map.get(node_id)
    while current_node:
        result.append(SimpleMessageModel.from_message_model(message=current_node))
        if current_node.thinking_log:
            result.extend(
                log
                for log in reversed(current_node.thinking_log)
                if any(
                    isinstance(content, ToolUseContentModel)
                    or isinstance(content, ToolResultContentModel)
                    for content in log.content
                )
            )

        parent_id = current_node.parent
        if parent_id is None:
            break
        current_node = message_map.get(parent_id)

    return result[::-1]


def chat(
    user: User,
    chat_input: ChatInput,
    on_stream: Callable[[str], None] | None = None,
    on_stop: Callable[[OnStopInput], None] | None = None,
    on_thinking: Callable[[OnThinking], None] | None = None,
    on_tool_result: Callable[[ToolRunResult], None] | None = None,
    on_reasoning: Callable[[str], None] | None = None,
) -> tuple[ConversationModel, MessageModel]:
    user_msg_id, conversation, bot = prepare_conversation(user, chat_input)

    # # Set tools only when tooluse is supported
    tools: Dict[str, AgentTool] = {}
    if is_tooluse_supported(chat_input.message.model):
        # Enable all tools for normal chat when no bot is selected
        enable_all_for_normal_chat = bot is None
        tools = get_tools(bot, enable_all_for_normal_chat=enable_all_for_normal_chat)

    display_citation = bot is not None and bot.display_retrieved_chunks

    message_map = conversation.message_map
    instructions: list[str] = (
        [
            content.body
            for content in message_map["instruction"].content
            if isinstance(content, TextContentModel)
        ]
        if "instruction" in message_map
        else []
    )
    
    # Add system instructions for normal chat with tools
    if bot is None and tools:
        normal_chat_instruction = """You are a helpful AI assistant. When responding to user queries:

1. FIRST provide a direct, helpful text response to answer their question or fulfill their request.

2. ONLY use tools when the user explicitly asks for content creation (documents, images, videos) or when a text response alone cannot adequately address their request.

3. For informational queries, provide the information directly in text format.

4. After providing a text response, you may optionally suggest creating related documents, images, or presentations if it would be genuinely helpful.

Available tools for content creation:
- Image generation (for creating visual content)
- Video generation (for creating video clips - keep prompts under 512 characters)  
- Excel spreadsheets (for data tables and reports)
- Word documents (for formatted text documents)
- PowerPoint presentations (for slide presentations)

IMPORTANT: When you use tools to create content (images, videos, documents), you MUST include the s3 download links in your final text response to the user. The tool results will contain a 'source_link' field with the s3 presigned URL - include this URL in your response so users can access their generated content directly. For example: "I've created your image! You can download it here: [s3 presigned url URL]" or "Your Excel file is ready: [s3 presigned URL]".

Remember: Always prioritize giving a direct text answer first, then offer additional content creation if relevant."""
        
        instructions.append(normal_chat_instruction)
        
      

    related_documents: list[RelatedDocumentModel] = []
    search_results: list[SearchResult] = []
    if bot is not None:
        if bot.is_agent_enabled() and is_tooluse_supported(chat_input.message.model):
            # If it have a knowledge base, always process it in agent mode
            if bot.has_knowledge():
                # Add knowledge tool
                knowledge_tool = create_knowledge_tool(bot=bot)
                tools[knowledge_tool.name] = knowledge_tool

            if display_citation:
                instructions.append(
                    get_prompt_to_cite_tool_results(
                        model=chat_input.message.model,
                    )
                )
        elif bot.has_knowledge() and not is_tooluse_supported(chat_input.message.model):
            # Fetch most related documents from vector store
            # NOTE: Currently embedding not support multi-modal. For now, use the last content.
            content = conversation.message_map[user_msg_id].content[-1]
            if isinstance(content, TextContentModel):
                pseudo_tool_use_id = "new-message-assistant"

                if on_thinking:
                    on_thinking(
                        {
                            "tool_use_id": pseudo_tool_use_id,
                            "name": "knowledge_base_tool",
                            "input": {
                                "query": content.body,
                            },
                        }
                    )

                search_results = search_related_docs(bot=bot, query=content.body)
                logger.info(f"Search results from vector store: {search_results}")

                if on_tool_result:
                    on_tool_result(
                        {
                            "tool_use_id": pseudo_tool_use_id,
                            "status": "success",
                            "related_documents": [
                                search_result_to_related_document(
                                    search_result=result,
                                    source_id_base=pseudo_tool_use_id,
                                )
                                for result in search_results
                            ],
                        }
                    )

                # Insert contexts to instruction
                instructions.append(
                    build_rag_prompt(
                        search_results=search_results,
                        model=chat_input.message.model,
                        display_citation=display_citation,
                    )
                )

    # Leaf node id
    # If `continue_generate` is True, note that new message is not added to the message map.
    node_id = (
        chat_input.message.parent_message_id
        if chat_input.continue_generate
        else message_map[user_msg_id].parent
    )
    if node_id is None:
        raise ValueError("parent_message_id or parent is None")

    messages = trace_to_root(
        node_id=node_id,
        message_map=message_map,
    )

    continue_generate = chat_input.continue_generate

    if continue_generate:
        message_for_continue_generate = SimpleMessageModel.from_message_model(
            message=message_map[conversation.last_message_id],
        )

    else:
        messages.append(
            SimpleMessageModel.from_message_model(message=message_map[user_msg_id]),
        )
        message_for_continue_generate = None

    generation_params = bot.generation_params if bot else None

    # Guardrails
    guardrail = bot.bedrock_guardrails if bot else None
    grounding_source = None
    if guardrail and guardrail.is_guardrail_enabled:
        grounding_source = to_guardrails_grounding_source(search_results)

    stream_handler = ConverseApiStreamHandler(
        model=chat_input.message.model,
        instructions=instructions,
        generation_params=generation_params,
        guardrail=guardrail,
        tools=tools,
        on_stream=on_stream,
        on_thinking=on_thinking,
        on_reasoning=on_reasoning,
    )

    thinking_log: list[SimpleMessageModel] = []
    while True:
        # Resolve S3 attachments before sending to Bedrock
        resolved_messages = resolve_s3_attachments_in_messages(messages)
        
        result = stream_handler.run(
            messages=resolved_messages,
            grounding_source=grounding_source,
            message_for_continue_generate=message_for_continue_generate,
            enable_reasoning=chat_input.enable_reasoning,
            prompt_caching_enabled=(
                bot.prompt_caching_enabled if bot is not None else True
            ),
        )

        message = result["message"]
        stop_reason = result["stop_reason"]

        conversation.total_price += result["price"]
        conversation.should_continue = stop_reason == "max_tokens"

        if stop_reason != "tool_use":  # Tool use converged
            message.parent = user_msg_id

            # If there is a thinking_log that includes reasoning, add it to the beginning of the content.
            reasoning_log = next(
                (
                    log
                    for log in thinking_log
                    if any(
                        isinstance(content, ReasoningContentModel)
                        for content in log.content
                    )
                ),
                None,
            )
            if reasoning_log:
                reasoning_content = next(
                    content
                    for content in reasoning_log.content
                    if isinstance(content, ReasoningContentModel)
                )
                message.content.insert(0, reasoning_content)

            # Retain tool use and its result logs
            tool_logs = [
                log
                for log in thinking_log
                if any(
                    isinstance(content, (ToolUseContentModel, ToolResultContentModel))
                    for content in log.content
                )
            ]
            if tool_logs:
                message.thinking_log = tool_logs

            if chat_input.continue_generate:
                # For continue generate
                if len(thinking_log) == 0:
                    assistant_msg_id = conversation.last_message_id
                    conversation.message_map[assistant_msg_id] = message
                    break

                else:
                    old_assistant_msg_id = conversation.last_message_id
                    conversation.message_map[user_msg_id].children.remove(
                        old_assistant_msg_id
                    )
                    del conversation.message_map[old_assistant_msg_id]

            # Issue id for new assistant message
            assistant_msg_id = str(ULID())
            conversation.message_map[assistant_msg_id] = message

            # Append children to parent
            conversation.message_map[user_msg_id].children.append(assistant_msg_id)
            conversation.last_message_id = assistant_msg_id

            search_results_as_related_documents = [
                search_result_to_related_document(
                    search_result=result,
                    source_id_base=assistant_msg_id,
                )
                for result in search_results
            ]
            related_documents.extend(search_results_as_related_documents)
            break

        tool_use_message = SimpleMessageModel.from_message_model(message=message)
        if continue_generate:
            messages[-1] = tool_use_message

            continue_generate = False
            message_for_continue_generate = None

        else:
            messages.append(tool_use_message)

        thinking_log.append(tool_use_message)

        tool_use_contents = [
            content
            for content in tool_use_message.content
            if isinstance(content, ToolUseContentModel)
        ]

        run_results: list[ToolRunResult] = []
        for content in tool_use_contents:
            tool = tools[content.body.name]
            run_result = tool.run(
                tool_use_id=content.body.tool_use_id,
                input=content.body.input,
                model=chat_input.message.model,
                bot=bot,
            )
            run_results.append(run_result)

            if run_result["status"] == "success":
                related_documents.extend(run_result["related_documents"])

            if on_tool_result:
                on_tool_result(run_result)

        tool_result_message = SimpleMessageModel(
            role="user",
            content=[
                ToolResultContentModel.from_tool_run_result(
                    run_result=result,
                    model=chat_input.message.model,
                    display_citation=display_citation,
                )
                for result in run_results
            ],
        )
        messages.append(tool_result_message)
        thinking_log.append(tool_result_message)

    # Store conversation before finish streaming so that front-end can avoid 404 issue
    store_conversation(user.id, conversation)
    store_related_documents(
        user_id=user.id,
        conversation_id=conversation.id,
        related_documents=related_documents,
    )

    if on_stop:
        on_stop(result)

    # Update bot last used time
    if bot:
        logger.info("Bot is provided. Updating bot last used time.")
        # Update bot last used time
        modify_bot_last_used_time(user, bot)
        # Update bot stats
        modify_bot_stats(user, bot, increment=1)

    return conversation, message


def chat_output_from_message(
    conversation: ConversationModel,
    message: MessageModel,
) -> ChatOutput:
    return ChatOutput(
        conversation_id=conversation.id,
        create_time=conversation.create_time,
        message=MessageOutput(
            role=message.role,
            content=[c.to_content() for c in message.content],
            model=message.model,
            children=message.children,
            parent=message.parent,
            feedback=None,
            used_chunks=(
                [
                    Chunk(
                        content=c.content,
                        content_type=c.content_type,
                        source=c.source,
                        rank=c.rank,
                    )
                    for c in message.used_chunks
                ]
                if message.used_chunks
                else None
            ),
            thinking_log=(
                [m.to_schema() for m in message.thinking_log]
                if message.thinking_log
                else None
            ),
        ),
        bot_id=conversation.bot_id,
    )


def propose_conversation_title(
    user_id: str,
    conversation_id: str,
    model: type_model_name = "claude-v3-haiku",
) -> str:
    PROMPT = """Reading the conversation above, what is the appropriate title for the conversation? When answering the title, please follow the rules below:
<rules>
- Title length must be from 15 to 20 characters.
- Prefer more specific title than general. Your title should always be distinct from others.
- Return the conversation title only. DO NOT include any strings other than the title.
- Title must be in the same language as the conversation.
</rules>
"""
    # Fetch existing conversation
    conversation = find_conversation_by_id(user_id, conversation_id)

    messages = trace_to_root(
        node_id=conversation.last_message_id,
        message_map=conversation.message_map,
    )

    # Append message to generate title
    new_message = SimpleMessageModel(
        role="user",
        content=[
            TextContentModel(
                content_type="text",
                body=PROMPT,
            )
        ],
    )
    messages.append(new_message)

    # Invoke Bedrock
    args = compose_args_for_converse_api(
        messages=[
            message
            for message in messages
            if not any(
                isinstance(content, ToolUseContentModel)
                or isinstance(content, ToolResultContentModel)
                or isinstance(content, ReasoningContentModel)
                for content in message.content
            )
        ],
        model=model,
        stream=False,
    )
    response = call_converse_api(args)
    reply_txt = (
        response["output"]["message"]["content"][0]["text"]
        if "message" in response["output"]
        and len(response["output"]["message"]["content"]) > 0
        and "text" in response["output"]["message"]["content"][0]
        else ""
    )

    return reply_txt


def fetch_conversation(user_id: str, conversation_id: str) -> Conversation:
    conversation = find_conversation_by_id(user_id, conversation_id)

    def process_content_with_presigned_urls(content_items):
        """Process content items and generate presigned URLs for S3 attachments"""
        processed_content = []
        for c in content_items:
            content = c.to_content()
            # If it's an S3 attachment, generate presigned URL
            if hasattr(content, 'content_type') and content.content_type == 's3_attachment':
                from app.utils_s3_documents import get_document_presigned_download_url
                try:
                    # Generate presigned URL and update the content
                    download_url = get_document_presigned_download_url(content.s3_key)
                    # Add download_url to the content (frontend expects this)
                    content.download_url = download_url
                except Exception as e:
                    logger.error(f"Failed to generate presigned URL for {content.s3_key}: {e}")
                    # Keep the content but without download_url
            processed_content.append(content)
        return processed_content

    message_map = {
        message_id: MessageOutput(
            role=message.role,
            content=process_content_with_presigned_urls(message.content),
            model=message.model,
            children=message.children,
            parent=message.parent,
            feedback=(
                FeedbackOutput(
                    thumbs_up=message.feedback.thumbs_up,
                    category=message.feedback.category,
                    comment=message.feedback.comment,
                )
                if message.feedback
                else None
            ),
            used_chunks=(
                [
                    Chunk(
                        content=c.content,
                        content_type=c.content_type,
                        source=c.source,
                        rank=c.rank,
                    )
                    for c in message.used_chunks
                ]
                if message.used_chunks
                else None
            ),
            thinking_log=(
                [m.to_schema() for m in message.thinking_log]
                if message.thinking_log
                else None
            ),
        )
        for message_id, message in conversation.message_map.items()
    }
    # Omit instruction
    if "instruction" in message_map:
        for c in message_map["instruction"].children:
            message_map[c].parent = "system"
        message_map["system"].children = message_map["instruction"].children

        del message_map["instruction"]

    output = Conversation(
        id=conversation_id,
        title=conversation.title,
        create_time=conversation.create_time,
        last_message_id=conversation.last_message_id,
        message_map=message_map,
        bot_id=conversation.bot_id,
        should_continue=conversation.should_continue,
    )
    return output


def search_conversations(query: str, user: User) -> list[ConversationSearchResult]:
    """Search conversations by keyword"""
    conversations = find_conversations_by_query(query, user)
    output = []

    for conversation in conversations:
        # Convert model SearchHighlightModel to schema SearchHighlight
        schema_highlights = None
        if conversation.highlights:
            schema_highlights = [
                SearchHighlight(
                    field_name=highlight.field_name, fragments=highlight.fragments
                )
                for highlight in conversation.highlights
            ]

        # Create ConversationSearchResult with properly converted highlights
        output.append(
            ConversationSearchResult(
                id=conversation.id,
                title=conversation.title,
                last_updated_time=conversation.last_updated_time,
                bot_id=conversation.bot_id,
                highlights=schema_highlights,
            )
        )

    return output


def resolve_s3_attachments_in_messages(
    messages: list[SimpleMessageModel],
) -> list[SimpleMessageModel]:
    """
    Resolve S3 attachments by downloading them and converting to regular attachments.
    This is needed because Bedrock Converse API doesn't support S3 references directly.
    """
    import base64
    
    resolved_messages = []
    
    for message in messages:
        resolved_content = []
        
        for content in message.content:
            if isinstance(content, S3AttachmentContentModel):
                try:
                    # Download the file from S3 document bucket
                    from app.utils_s3_documents import download_document_from_s3
                    file_content = download_document_from_s3(content.s3_key)
                    
                    # Convert to regular attachment - pass bytes directly
                    attachment_content = AttachmentContentModel(
                        content_type="attachment",
                        file_name=content.file_name,
                        body=file_content,
                    )
                    resolved_content.append(attachment_content)
                    
                    logger.info(f"Resolved S3 attachment: {content.file_name}, size: {len(file_content)} bytes")
                    
                except Exception as e:
                    logger.error(f"Failed to resolve S3 attachment {content.file_name}: {e}")
                    # Skip this attachment if we can't resolve it
                    continue
            else:
                resolved_content.append(content)
        
        resolved_messages.append(
            SimpleMessageModel(
                role=message.role,
                content=resolved_content,
            )
        )
    
    return resolved_messages