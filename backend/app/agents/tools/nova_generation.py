import logging
import json
import base64
import random
import os
import uuid
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

import boto3
from app.agents.tools.agent_tool import AgentTool
from app.repositories.models.custom_bot import BotModel
from app.routes.schemas.conversation import type_model_name
from app.utils import generate_presigned_url, BEDROCK_REGION
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Use the same document bucket for storing generated images and videos
DOCUMENT_BUCKET = os.environ.get("DOCUMENT_BUCKET", f"bedrock-chat-documents-{os.environ.get('ENV_NAME', 'default')}")

# Nova model IDs
NOVA_CANVAS_MODEL_ID = "amazon.nova-canvas-v1:0"
NOVA_REEL_MODEL_ID = "amazon.nova-reel-v1:0"


def _upload_media_to_s3(media_data: bytes, filename: str, content_type: str, media_type: str = "image") -> str:
    """
    Upload media (image/video) to S3 and return presigned download URL.
    
    Args:
        media_data: Binary media data
        filename: Name of the file
        content_type: MIME type of the media
        media_type: Type of media ("image" or "video")
        
    Returns:
        str: Presigned download URL
    """
    try:
        logger.info(f"Attempting to upload {media_type} to bucket: {DOCUMENT_BUCKET}")
        
        # Generate unique S3 key with timestamp and UUID to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        s3_key = f"generated_{media_type}s/{timestamp}_{unique_id}_{filename}"
        
        # Create S3 client
        s3_client = boto3.client("s3", region_name=BEDROCK_REGION)
        
        # Upload to S3
        s3_client.put_object(
            Bucket=DOCUMENT_BUCKET,
            Key=s3_key,
            Body=media_data,
            ContentType=content_type,
            # Set expiration for cleanup (30 days)
            Expires=datetime.now().timestamp() + (30 * 24 * 60 * 60)
        )
        
        # Generate presigned download URL (valid for 24 hours)
        download_url = generate_presigned_url(
            bucket=DOCUMENT_BUCKET,
            key=s3_key,
            expiration=24 * 60 * 60,  # 24 hours
            client_method="get_object"
        )
        
        logger.info(f"{media_type.capitalize()} uploaded successfully to S3: {s3_key}")
        return download_url
        
    except Exception as e:
        logger.error(f"Error uploading {media_type} to S3: {e}")
        raise e


class NovaCanvasInput(BaseModel):
    prompt: str = Field(description="Text prompt describing the image to generate")
    width: int = Field(default=1024, description="Width of the generated image (512, 768, 1024, 1152, 1216, 1344, 1536)")
    height: int = Field(default=1024, description="Height of the generated image (512, 768, 1024, 1152, 1216, 1344, 1536)")
    quality: str = Field(default="standard", description="Quality of the generated image ('standard' or 'premium')")
    cfg_scale: float = Field(default=7.0, description="How closely the image should follow the prompt (1.0 to 10.0)")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducible results")


class NovaReelInput(BaseModel):
    prompt: str = Field(description="Text prompt describing the video to generate")
    duration_seconds: int = Field(default=6, description="Duration of the video in seconds (currently only 6 seconds supported)")
    fps: int = Field(default=24, description="Frames per second (currently only 24 fps supported)")
    dimension: str = Field(default="1280x720", description="Video dimensions (currently only '1280x720' supported)")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducible results")


def _generate_image_with_nova_canvas(tool_input: NovaCanvasInput, bot: BotModel | None, model: type_model_name | None) -> Dict[str, Any]:
    """Generate an image using Amazon Nova Canvas."""
    try:
        logger.info(f"Generating image with Nova Canvas: {tool_input.prompt[:100]}...")
        
        # Create Bedrock Runtime client
        bedrock_client = boto3.client('bedrock-runtime', region_name=BEDROCK_REGION)
        
        # Prepare request body
        request_body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": tool_input.prompt
            },
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "quality": tool_input.quality,
                "height": tool_input.height,
                "width": tool_input.width,
                "cfgScale": tool_input.cfg_scale,
                "seed": tool_input.seed if tool_input.seed is not None else random.randint(1, 2147483647),
            }
        }
        
        # Call Nova Canvas
        response = bedrock_client.invoke_model(
            modelId=NOVA_CANVAS_MODEL_ID,
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        base64_image = response_body['images'][0]
        
        # Decode image data
        image_data = base64.b64decode(base64_image)
        
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nova_canvas_image_{timestamp}.png"
        
        # Upload to S3 and get download URL
        download_url = _upload_media_to_s3(
            media_data=image_data,
            filename=filename,
            content_type="image/png",
            media_type="image"
        )
        
        logger.info(f"Generated presigned URL for Nova Canvas image: {download_url}")
        
        # Return result with download link and image data for inline display
        result = {
            "content": f"Image generated successfully using Nova Canvas with prompt: '{tool_input.prompt}'. Dimensions: {tool_input.width}x{tool_input.height}, Quality: {tool_input.quality}",
            "source_name": filename,
            "source_link": download_url,
            "media_type": "image",
            "image_data": base64_image  # Include base64 data for inline display
        }
        
        logger.info(f"Returning Nova Canvas result: {result['content']}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating image with Nova Canvas: {e}")
        raise e


def _generate_video_with_nova_reel(tool_input: NovaReelInput, bot: BotModel | None, model: type_model_name | None) -> Dict[str, Any]:
    """Generate a video using Amazon Nova Reel."""
    try:
        logger.info(f"Generating video with Nova Reel: {tool_input.prompt[:100]}...")
        
        # Create Bedrock Runtime client
        bedrock_client = boto3.client('bedrock-runtime', region_name=BEDROCK_REGION)
        
        # Prepare model input
        model_input = {
            "taskType": "TEXT_VIDEO",
            "textToVideoParams": {
                "text": tool_input.prompt,
            },
            "videoGenerationConfig": {
                "durationSeconds": tool_input.duration_seconds,
                "fps": tool_input.fps,
                "dimension": tool_input.dimension,
                "seed": tool_input.seed if tool_input.seed is not None else random.randint(0, 2147483648),
            },
        }
        
        # Start asynchronous video generation job
        invocation = bedrock_client.start_async_invoke(
            modelId=NOVA_REEL_MODEL_ID,
            modelInput=model_input,
            outputDataConfig={"s3OutputDataConfig": {"s3Uri": f"s3://{DOCUMENT_BUCKET}/nova_reel_temp/"}}
        )
        
        invocation_arn = invocation["invocationArn"]
        invocation_id = invocation_arn.split("/")[-1]
        
        logger.info(f"Started Nova Reel job with ARN: {invocation_arn}")
        
        # Monitor job status and wait for completion
        max_wait_time = 300  # 5 minutes max wait
        check_interval = 10  # Check every 10 seconds
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            job_status = bedrock_client.get_async_invoke(invocationArn=invocation_arn)
            status = job_status["status"]
            
            logger.info(f"Nova Reel job status: {status} (elapsed: {elapsed_time}s)")
            
            if status == "Completed":
                # Job completed successfully
                break
            elif status == "Failed":
                error_message = job_status.get("failureMessage", "Unknown error")
                raise Exception(f"Nova Reel job failed: {error_message}")
            elif status == "InProgress":
                # Continue waiting
                time.sleep(check_interval)
                elapsed_time += check_interval
            else:
                raise Exception(f"Unexpected job status: {status}")
        
        if elapsed_time >= max_wait_time:
            raise Exception("Nova Reel job timed out after 5 minutes")
        
        # Download the generated video from S3
        s3_client = boto3.client("s3", region_name=BEDROCK_REGION)
        
        # List objects with the invocation ID prefix
        response = s3_client.list_objects_v2(
            Bucket=DOCUMENT_BUCKET, 
            Prefix=f"nova_reel_temp/{invocation_id}"
        )
        
        video_key = None
        for obj in response.get("Contents", []):
            if obj["Key"].endswith(".mp4"):
                video_key = obj["Key"]
                break
        
        if not video_key:
            raise Exception("Generated video file not found in S3")
        
        # Download video data
        video_obj = s3_client.get_object(Bucket=DOCUMENT_BUCKET, Key=video_key)
        video_data = video_obj['Body'].read()
        
        # Create final filename and upload to proper location
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nova_reel_video_{timestamp}.mp4"
        
        # Upload to final location
        download_url = _upload_media_to_s3(
            media_data=video_data,
            filename=filename,
            content_type="video/mp4",
            media_type="video"
        )
        
        # Clean up temporary file
        try:
            s3_client.delete_object(Bucket=DOCUMENT_BUCKET, Key=video_key)
        except Exception as cleanup_error:
            logger.warning(f"Failed to clean up temporary video file: {cleanup_error}")
        
        logger.info(f"Generated presigned URL for Nova Reel video: {download_url}")
        
        # Return result with download link
        result = {
            "content": f"Video generated successfully using Nova Reel with prompt: '{tool_input.prompt}'. Duration: {tool_input.duration_seconds}s, Dimensions: {tool_input.dimension}, FPS: {tool_input.fps}",
            "source_name": filename,
            "source_link": download_url,
            "media_type": "video"
        }
        
        logger.info(f"Returning Nova Reel result: {result['content']}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating video with Nova Reel: {e}")
        raise e


# Create the agent tools
nova_canvas_tool = AgentTool(
    name="nova_canvas",
    description="Generate images from text prompts using Amazon Nova Canvas. Useful for creating visual content, illustrations, artwork, and any image-based requests.",
    args_schema=NovaCanvasInput,
    function=_generate_image_with_nova_canvas,
)

nova_reel_tool = AgentTool(
    name="nova_reel",
    description="Generate short videos from text prompts using Amazon Nova Reel. Useful for creating video content, animations, and visual storytelling. Currently supports 6-second videos at 1280x720 resolution.",
    args_schema=NovaReelInput,
    function=_generate_video_with_nova_reel,
)