from app.bedrock import (
    generate_image_with_nova_canvas,
    generate_video_with_nova_reel,
    calculate_media_generation_price,
    is_nova_canvas_model,
    is_nova_reel_model,
)
from app.repositories.conversation import (
    find_conversation_by_id,
    store_conversation,
)
from app.repositories.models.conversation import (
    ConversationModel,
    MessageModel,
    TextContentModel,
    ImageGenerationRequestContentModel,
    ImageGenerationResponseContentModel,
    VideoGenerationRequestContentModel,
    VideoGenerationResponseContentModel,
)
from app.routes.schemas.conversation import (
    ChatInput,
    ChatOutput,
    type_model_name,
)
from app.usecases.chat import chat_output_from_message
from app.user import User
from app.utils import get_current_time
from fastapi import APIRouter, Request, HTTPException
from ulid import ULID
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(tags=["media_generation"])


@router.post("/generate-image", response_model=ChatOutput)
def generate_image(request: Request, chat_input: ChatInput):
    """Generate an image using Amazon Nova Canvas"""
    current_user: User = request.state.current_user
    
    # Validate that the model is Nova Canvas
    if not is_nova_canvas_model(chat_input.message.model):
        raise HTTPException(
            status_code=400,
            detail=f"Model {chat_input.message.model} is not supported for image generation"
        )
    
    # Extract image generation request from the message content
    image_request = None
    for content in chat_input.message.content:
        if content.content_type == "image_generation_request":
            image_request = content
            break
    
    if not image_request:
        raise HTTPException(
            status_code=400,
            detail="No image generation request found in message content"
        )
    
    try:
        # Generate the image
        result = generate_image_with_nova_canvas(
            prompt=image_request.prompt,
            negative_prompt=image_request.negative_prompt,
            width=image_request.width,
            height=image_request.height,
            cfg_scale=image_request.cfg_scale,
            seed=image_request.seed,
        )
        
        # Get or create conversation
        current_time = get_current_time()
        try:
            conversation = find_conversation_by_id(current_user.id, chat_input.conversation_id)
        except:
            # Create new conversation for image generation
            conversation = ConversationModel(
                id=chat_input.conversation_id,
                title="Image Generation",
                total_price=0.0,
                create_time=current_time,
                message_map={
                    "system": MessageModel(
                        role="system",
                        content=[TextContentModel(content_type="text", body="")],
                        model=chat_input.message.model,
                        children=[],
                        parent=None,
                        create_time=current_time,
                        feedback=None,
                        used_chunks=None,
                        thinking_log=None,
                    )
                },
                last_message_id="",
                bot_id=chat_input.bot_id,
                should_continue=False,
            )
        
        # Add user message with image generation request
        user_message_id = str(ULID())
        user_message = MessageModel(
            role="user",
            content=[
                ImageGenerationRequestContentModel(
                    content_type="image_generation_request",
                    prompt=image_request.prompt,
                    negative_prompt=image_request.negative_prompt,
                    width=image_request.width,
                    height=image_request.height,
                    cfg_scale=image_request.cfg_scale,
                    seed=image_request.seed,
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
        
        # Add assistant message with generated image
        assistant_message_id = str(ULID())
        assistant_message = MessageModel(
            role="assistant",
            content=[
                ImageGenerationResponseContentModel(
                    content_type="image_generation_response",
                    image_data=result["image_data"],
                    media_type="image/png",
                    prompt=result["prompt"],
                    seed=result["seed"],
                )
            ],
            model=chat_input.message.model,
            children=[],
            parent=user_message_id,
            create_time=current_time,
            feedback=None,
            used_chunks=None,
            thinking_log=None,
        )
        
        # Update conversation
        conversation.message_map[user_message_id] = user_message
        conversation.message_map[assistant_message_id] = assistant_message
        conversation.message_map["system"].children.append(user_message_id)
        user_message.children.append(assistant_message_id)
        conversation.last_message_id = assistant_message_id
        
        # Calculate and add price
        price = calculate_media_generation_price(chat_input.message.model)
        conversation.total_price += price
        
        # Store conversation
        store_conversation(current_user.id, conversation)
        
        # Return response
        return chat_output_from_message(conversation=conversation, message=assistant_message)
        
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate image: {str(e)}")


@router.post("/generate-video", response_model=ChatOutput)
def generate_video(request: Request, chat_input: ChatInput):
    """Generate a video using Amazon Nova Reel"""
    current_user: User = request.state.current_user
    
    # Validate that the model is Nova Reel
    if not is_nova_reel_model(chat_input.message.model):
        raise HTTPException(
            status_code=400,
            detail=f"Model {chat_input.message.model} is not supported for video generation"
        )
    
    # Extract video generation request from the message content
    video_request = None
    for content in chat_input.message.content:
        if content.content_type == "video_generation_request":
            video_request = content
            break
    
    if not video_request:
        raise HTTPException(
            status_code=400,
            detail="No video generation request found in message content"
        )
    
    try:
        # Generate the video
        result = generate_video_with_nova_reel(
            prompt=video_request.prompt,
            negative_prompt=video_request.negative_prompt,
            duration_seconds=video_request.duration_seconds,
            fps=video_request.fps,
            seed=video_request.seed,
        )
        
        # Get or create conversation
        current_time = get_current_time()
        try:
            conversation = find_conversation_by_id(current_user.id, chat_input.conversation_id)
        except:
            # Create new conversation for video generation
            conversation = ConversationModel(
                id=chat_input.conversation_id,
                title="Video Generation",
                total_price=0.0,
                create_time=current_time,
                message_map={
                    "system": MessageModel(
                        role="system",
                        content=[TextContentModel(content_type="text", body="")],
                        model=chat_input.message.model,
                        children=[],
                        parent=None,
                        create_time=current_time,
                        feedback=None,
                        used_chunks=None,
                        thinking_log=None,
                    )
                },
                last_message_id="",
                bot_id=chat_input.bot_id,
                should_continue=False,
            )
        
        # Add user message with video generation request
        user_message_id = str(ULID())
        user_message = MessageModel(
            role="user",
            content=[
                VideoGenerationRequestContentModel(
                    content_type="video_generation_request",
                    prompt=video_request.prompt,
                    negative_prompt=video_request.negative_prompt,
                    duration_seconds=video_request.duration_seconds,
                    fps=video_request.fps,
                    seed=video_request.seed,
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
        
        # Add assistant message with generated video
        assistant_message_id = str(ULID())
        assistant_message = MessageModel(
            role="assistant",
            content=[
                VideoGenerationResponseContentModel(
                    content_type="video_generation_response",
                    video_data=result["video_data"],
                    media_type="video/mp4",
                    prompt=result["prompt"],
                    duration_seconds=result["duration_seconds"],
                    seed=result["seed"],
                )
            ],
            model=chat_input.message.model,
            children=[],
            parent=user_message_id,
            create_time=current_time,
            feedback=None,
            used_chunks=None,
            thinking_log=None,
        )
        
        # Update conversation
        conversation.message_map[user_message_id] = user_message
        conversation.message_map[assistant_message_id] = assistant_message
        conversation.message_map["system"].children.append(user_message_id)
        user_message.children.append(assistant_message_id)
        conversation.last_message_id = assistant_message_id
        
        # Calculate and add price
        price = calculate_media_generation_price(chat_input.message.model)
        conversation.total_price += price
        
        # Store conversation
        store_conversation(current_user.id, conversation)
        
        # Return response
        return chat_output_from_message(conversation=conversation, message=assistant_message)
        
    except Exception as e:
        logger.error(f"Error generating video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate video: {str(e)}")