from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, Dict, Optional, Literal, Tuple, TypeGuard

from app.config import (
    BEDROCK_PRICING,
    DEFAULT_DEEP_SEEK_GENERATION_CONFIG,
    DEFAULT_GENERATION_CONFIG,
    DEFAULT_LLAMA_GENERATION_CONFIG,
    DEFAULT_MISTRAL_GENERATION_CONFIG,
)
from app.repositories.models.custom_bot import GenerationParamsModel
from app.repositories.models.custom_bot_guardrails import BedrockGuardrailsModel
from app.routes.schemas.conversation import type_model_name
from app.utils import get_bedrock_runtime_client
from botocore.exceptions import ClientError
from reretry import retry
import base64
import json
import random

if TYPE_CHECKING:
    from app.agents.tools.agent_tool import AgentTool
    from app.repositories.models.conversation import ContentModel, SimpleMessageModel
    from mypy_boto3_bedrock_runtime.literals import ConversationRoleType
    from mypy_boto3_bedrock_runtime.type_defs import (
        ContentBlockTypeDef,
        ConverseResponseTypeDef,
        ConverseStreamRequestTypeDef,
        GuardrailConverseContentBlockTypeDef,
        InferenceConfigurationTypeDef,
        MessageTypeDef,
        SystemContentBlockTypeDef,
        ToolTypeDef,
    )


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
ENABLE_BEDROCK_CROSS_REGION_INFERENCE = (
    os.environ.get("ENABLE_BEDROCK_CROSS_REGION_INFERENCE", "false") == "true"
)

client = get_bedrock_runtime_client()


class BedrockThrottlingException(Exception): ...


def _is_conversation_role(role: str) -> TypeGuard[ConversationRoleType]:
    return role in ["user", "assistant"]


def is_nova_model(model: type_model_name) -> bool:
    """Check if the model is an Amazon Nova model"""
    return "amazon-nova" in model


def is_nova_canvas_model(model: type_model_name) -> bool:
    """Check if the model is Amazon Nova Canvas (image generation)"""
    return model == "amazon-nova-canvas"


def is_nova_reel_model(model: type_model_name) -> bool:
    """Check if the model is Amazon Nova Reel (video generation)"""
    return model == "amazon-nova-reel"


def is_media_generation_model(model: type_model_name) -> bool:
    """Check if the model is for media generation (image or video)"""
    return is_nova_canvas_model(model) or is_nova_reel_model(model)


def is_deepseek_model(model: type_model_name) -> bool:
    """Check if the model is a DeepSeek model"""
    return "deepseek" in model


def is_llama_model(model: type_model_name) -> bool:
    """Check if the model is a Meta Llama model"""
    return "llama" in model


def is_mistral(model: type_model_name) -> bool:
    """Check if the model is a Mistral model"""
    return "mistral" in model


def is_tooluse_supported(model: type_model_name) -> bool:
    """Check if the model is supported for tool use"""
    return model not in [
        "deepseek-r1",
        "llama3-2-1b-instruct",
        "llama3-2-3b-instruct",
        "",
    ]


def is_prompt_caching_supported(
    model: type_model_name, target: Literal["system", "message", "tool"]
) -> bool:
    if target == "tool":
        return model in [
            "claude-v4-opus",
            "claude-v4-sonnet",
            "claude-v3.7-sonnet",
            "claude-v3.5-sonnet-v2",
            "claude-v3.5-haiku",
        ]

    else:
        return model in [
            "claude-v4-opus",
            "claude-v4-sonnet",
            "claude-v3.7-sonnet",
            "claude-v3.5-sonnet-v2",
            "claude-v3.5-haiku",
            "amazon-nova-pro",
            "amazon-nova-lite",
            "amazon-nova-micro",
        ]


def _prepare_deepseek_model_params(
    model: type_model_name, generation_params: Optional[GenerationParamsModel] = None
) -> Tuple[InferenceConfigurationTypeDef, None]:
    """
    Prepare inference configuration and additional model request fields for DeepSeek models
    > Note that DeepSeek models expect inference parameters as a JSON object under an inferenceConfig attribute,
    > similar to Amazon Nova models.
    """
    # Base inference configuration
    inference_config: InferenceConfigurationTypeDef = {
        "maxTokens": (
            generation_params.max_tokens
            if generation_params
            else DEFAULT_DEEP_SEEK_GENERATION_CONFIG["max_tokens"]
        ),
        "temperature": (
            generation_params.temperature
            if generation_params
            else DEFAULT_DEEP_SEEK_GENERATION_CONFIG["temperature"]
        ),
        "topP": (
            generation_params.top_p
            if generation_params
            else DEFAULT_DEEP_SEEK_GENERATION_CONFIG["top_p"]
        ),
    }

    inference_config["stopSequences"] = (
        generation_params.stop_sequences
        if (
            generation_params
            and generation_params.stop_sequences
            and any(generation_params.stop_sequences)
        )
        else DEFAULT_DEEP_SEEK_GENERATION_CONFIG.get("stop_sequences", [])
    )

    return inference_config, None


def _prepare_mistral_model_params(
    model: type_model_name, generation_params: Optional[GenerationParamsModel] = None
) -> Tuple[InferenceConfigurationTypeDef, Dict[str, int] | None]:
    """
    Prepare inference configuration and additional model request fields for Mistral models
    > Note that Mistral models expect inference parameters as a JSON object under an inferenceConfig attribute,
    > similar to other models.
    """
    # Base inference configuration
    inference_config: InferenceConfigurationTypeDef = {
        "maxTokens": (
            generation_params.max_tokens
            if generation_params
            else DEFAULT_MISTRAL_GENERATION_CONFIG["max_tokens"]
        ),
        "temperature": (
            generation_params.temperature
            if generation_params
            else DEFAULT_MISTRAL_GENERATION_CONFIG["temperature"]
        ),
        "topP": (
            generation_params.top_p
            if generation_params
            else DEFAULT_MISTRAL_GENERATION_CONFIG["top_p"]
        ),
    }

    inference_config["stopSequences"] = (
        generation_params.stop_sequences
        if (
            generation_params
            and generation_params.stop_sequences
            and any(generation_params.stop_sequences)
        )
        else DEFAULT_MISTRAL_GENERATION_CONFIG.get("stop_sequences", [])
    )

    # Add top_k if specified in generation params
    additional_fields = None
    if generation_params and generation_params.top_k is not None:
        additional_fields = {"topK": generation_params.top_k}

    return inference_config, additional_fields


def _prepare_llama_model_params(
    model: type_model_name, generation_params: Optional[GenerationParamsModel] = None
) -> Tuple[InferenceConfigurationTypeDef, None]:
    """
    Prepare inference configuration and additional model request fields for Meta Llama models
    > Note that Llama models expect inference parameters as a JSON object under an inferenceConfig attribute,
    > similar to Amazon Nova models.
    """
    # Base inference configuration
    inference_config: InferenceConfigurationTypeDef = {
        "maxTokens": (
            generation_params.max_tokens
            if generation_params
            else DEFAULT_LLAMA_GENERATION_CONFIG["max_tokens"]
        ),
        "temperature": (
            generation_params.temperature
            if generation_params
            else DEFAULT_LLAMA_GENERATION_CONFIG["temperature"]
        ),
        "topP": (
            generation_params.top_p
            if generation_params
            else DEFAULT_LLAMA_GENERATION_CONFIG["top_p"]
        ),
    }

    inference_config["stopSequences"] = (
        generation_params.stop_sequences
        if (
            generation_params
            and generation_params.stop_sequences
            and any(generation_params.stop_sequences)
        )
        else DEFAULT_LLAMA_GENERATION_CONFIG.get("stop_sequences", [])
    )

    # No additional fields for Llama models
    additional_fields = None

    return inference_config, additional_fields


def _prepare_nova_model_params(
    model: type_model_name, generation_params: Optional[GenerationParamsModel] = None
) -> Tuple[InferenceConfigurationTypeDef, Dict[str, Any]]:
    """
    Prepare inference configuration and additional model request fields for Nova models
    > Note that Amazon Nova expects inference parameters as a JSON object under a inferenceConfig attribute. Amazon Nova also has an additional parameter "topK" that can be passed as an additional inference parameters. This parameter follows the same structure and is passed through the additionalModelRequestFields, as shown below.
    https://docs.aws.amazon.com/nova/latest/userguide/getting-started-converse.html
    """
    # Base inference configuration
    inference_config: InferenceConfigurationTypeDef = {
        "maxTokens": (
            generation_params.max_tokens
            if generation_params
            else DEFAULT_GENERATION_CONFIG["max_tokens"]
        ),
        "temperature": (
            generation_params.temperature
            if generation_params
            else DEFAULT_GENERATION_CONFIG["temperature"]
        ),
        "topP": (
            generation_params.top_p
            if generation_params
            else DEFAULT_GENERATION_CONFIG["top_p"]
        ),
    }

    # Additional model request fields specific to Nova models
    additional_fields: Dict[str, Any] = {"inferenceConfig": {}}

    # Add top_k if specified in generation params
    if generation_params and generation_params.top_k is not None:
        top_k = generation_params.top_k
        if top_k > 128:
            logger.warning(
                "In Amazon Nova, an 'unexpected error' occurs if topK exceeds 128. To avoid errors, the upper limit of A is set to 128."
            )
            top_k = 128

        additional_fields["inferenceConfig"]["topK"] = top_k

    return inference_config, additional_fields


def compose_args_for_converse_api(
    messages: list[SimpleMessageModel],
    model: type_model_name,
    instructions: list[str] = [],
    generation_params: GenerationParamsModel | None = None,
    guardrail: BedrockGuardrailsModel | None = None,
    grounding_source: GuardrailConverseContentBlockTypeDef | None = None,
    tools: dict[str, AgentTool] | None = None,
    stream: bool = True,
    enable_reasoning: bool = False,
    prompt_caching_enabled: bool = False,
) -> ConverseStreamRequestTypeDef:
    def process_content(c: ContentModel, role: str) -> list[ContentBlockTypeDef]:
        # Drop unsigned reasoning blocks only for DeepSeek R1
        if (
            is_deepseek_model(model)
            and c.content_type == "reasoning"
            and not getattr(c, "signature", None)
        ):
            return []

        if c.content_type == "text":
            if (
                role == "user"
                and guardrail
                and guardrail.grounding_threshold > 0
                and grounding_source
            ):
                return [
                    {"guardContent": grounding_source},
                    {
                        "guardContent": {
                            "text": {"text": c.body, "qualifiers": ["query"]}
                        }
                    },
                ]

        return c.to_contents_for_converse()

    arg_messages: list[MessageTypeDef] = [
        {
            "role": message.role,
            "content": [
                block
                for c in message.content
                for block in process_content(c, message.role)
            ],
        }
        for message in messages
        if _is_conversation_role(message.role)
    ]
    tool_specs: list[ToolTypeDef] | None = (
        [
            {
                "toolSpec": tool.to_converse_spec(),
            }
            for tool in tools.values()
        ]
        if tools
        else None
    )

    # Prepare model-specific parameters
    inference_config: InferenceConfigurationTypeDef
    additional_model_request_fields: dict[str, Any] | None
    system_prompts: list[SystemContentBlockTypeDef]

    if is_nova_model(model):
        # Special handling for Nova models
        inference_config, additional_model_request_fields = _prepare_nova_model_params(
            model, generation_params
        )
        system_prompts = (
            [
                {
                    "text": "\n\n".join(instructions),
                }
            ]
            if instructions and any(instructions)
            else []
        )

    elif is_deepseek_model(model):
        # Special handling for DeepSeek models
        inference_config, additional_model_request_fields = (
            _prepare_deepseek_model_params(model, generation_params)
        )
        system_prompts = (
            [
                {
                    "text": "\n\n".join(instructions),
                }
            ]
            if instructions and any(instructions)
            else []
        )

    elif is_llama_model(model):
        # Special handling for Llama models
        inference_config, additional_model_request_fields = _prepare_llama_model_params(
            model, generation_params
        )
        system_prompts = (
            [
                {
                    "text": "\n\n".join(instructions),
                }
            ]
            if instructions and any(instructions)
            else []
        )

    elif is_mistral(model):
        # Special handling for Mistral models
        inference_config, additional_model_request_fields = (
            _prepare_mistral_model_params(model, generation_params)
        )
        system_prompts = (
            [
                {
                    "text": "\n\n".join(instructions),
                }
            ]
            if instructions and any(instructions)
            else []
        )

    else:
        # Standard handling for non-Nova models
        if enable_reasoning:
            budget_tokens = (
                generation_params.reasoning_params.budget_tokens
                if generation_params and generation_params.reasoning_params
                else DEFAULT_GENERATION_CONFIG["reasoning_params"]["budget_tokens"]  # type: ignore
            )
            max_tokens = (
                generation_params.max_tokens
                if generation_params
                else DEFAULT_GENERATION_CONFIG["max_tokens"]
            )

            if max_tokens <= budget_tokens:
                logger.warning(
                    f"max_tokens ({max_tokens}) must be greater than budget_tokens ({budget_tokens}). "
                    f"Setting max_tokens to {budget_tokens + 1024}"
                )
                max_tokens = budget_tokens + 1024

            inference_config = {
                "maxTokens": max_tokens,
                "temperature": 1.0,  # Force temperature to 1.0 when reasoning is enabled
                "topP": (
                    generation_params.top_p
                    if generation_params
                    else DEFAULT_GENERATION_CONFIG["top_p"]
                ),
                "stopSequences": (
                    generation_params.stop_sequences
                    if (
                        generation_params
                        and generation_params.stop_sequences
                        and any(generation_params.stop_sequences)
                    )
                    else DEFAULT_GENERATION_CONFIG.get("stop_sequences", [])
                ),
            }
            additional_model_request_fields = {
                # top_k cannot be used with reasoning
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": budget_tokens,
                },
            }
        else:
            inference_config = {
                "maxTokens": (
                    generation_params.max_tokens
                    if generation_params
                    else DEFAULT_GENERATION_CONFIG["max_tokens"]
                ),
                "temperature": (
                    generation_params.temperature
                    if generation_params
                    else DEFAULT_GENERATION_CONFIG["temperature"]
                ),
                "topP": (
                    generation_params.top_p
                    if generation_params
                    else DEFAULT_GENERATION_CONFIG["top_p"]
                ),
                "stopSequences": (
                    generation_params.stop_sequences
                    if (
                        generation_params
                        and generation_params.stop_sequences
                        and any(generation_params.stop_sequences)
                    )
                    else DEFAULT_GENERATION_CONFIG.get("stop_sequences", [])
                ),
            }
            additional_model_request_fields = {
                "top_k": (
                    generation_params.top_k
                    if generation_params
                    else DEFAULT_GENERATION_CONFIG["top_k"]
                ),
            }
        system_prompts = [
            {
                "text": instruction,
            }
            for instruction in instructions
            if len(instruction) > 0
        ]

    if prompt_caching_enabled and not (
        tool_specs and not is_prompt_caching_supported(model, target="tool")
    ):
        if is_prompt_caching_supported(model, "system") and len(system_prompts) > 0:
            system_prompts.append(
                {
                    "cachePoint": {
                        "type": "default",
                    },
                }
            )

        if is_prompt_caching_supported(model, target="message"):
            for order, message in enumerate(
                filter(lambda m: m["role"] == "user", reversed(arg_messages))
            ):
                if order >= 2:
                    break

                message["content"] = [
                    *(message["content"]),
                    {
                        "cachePoint": {"type": "default"},
                    },
                ]

        if is_prompt_caching_supported(model, target="tool") and tool_specs:
            tool_specs.append(
                {
                    "cachePoint": {
                        "type": "default",
                    },
                }
            )

    # Construct the base arguments
    args: ConverseStreamRequestTypeDef = {
        "inferenceConfig": inference_config,
        "modelId": get_model_id(model),
        "messages": arg_messages,
        "system": system_prompts,
    }

    if additional_model_request_fields is not None:
        args["additionalModelRequestFields"] = additional_model_request_fields

    if guardrail and guardrail.guardrail_arn and guardrail.guardrail_version:
        args["guardrailConfig"] = {
            "guardrailIdentifier": guardrail.guardrail_arn,
            "guardrailVersion": guardrail.guardrail_version,
            "trace": "enabled",
        }

        if stream:
            # https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-streaming.html
            args["guardrailConfig"]["streamProcessingMode"] = "async"

    # NOTE: Some models doesn't support tool use. https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-supported-models-features.html
    if tool_specs:
        args["toolConfig"] = {
            "tools": tool_specs,
        }

    return args


@retry(
    exceptions=(BedrockThrottlingException,),
    tries=3,
    delay=60,
    backoff=2,
    jitter=(0, 2),
    logger=logger,
)
def call_converse_api(
    args: ConverseStreamRequestTypeDef,
) -> ConverseResponseTypeDef:
    client = get_bedrock_runtime_client()
    try:
        return client.converse(**args)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ThrottlingException":
            raise BedrockThrottlingException(
                "Bedrock API is throttling requests"
            ) from e
        raise


def calculate_price(
    model: type_model_name,
    input_tokens: int,
    output_tokens: int,
    cache_read_input_tokens: int,
    cache_write_input_tokens: int,
    region: str = BEDROCK_REGION,
) -> float:
    input_price = (
        BEDROCK_PRICING.get(region, {})
        .get(model, {})
        .get("input", BEDROCK_PRICING["default"][model]["input"])
    )
    output_price = (
        BEDROCK_PRICING.get(region, {})
        .get(model, {})
        .get("output", BEDROCK_PRICING["default"][model]["output"])
    )
    cache_read_input_price = (
        BEDROCK_PRICING.get(region, {})
        .get(model, {})
        .get(
            "cache_read_input",
            BEDROCK_PRICING["default"][model].get("cache_read_input", input_price),
        )
    )
    cache_write_input_price = (
        BEDROCK_PRICING.get(region, {})
        .get(model, {})
        .get(
            "cache_write_input",
            BEDROCK_PRICING["default"][model].get("cache_write_input", input_price),
        )
    )

    return (
        input_price * input_tokens / 1000.0
        + output_price * output_tokens / 1000.0
        + cache_read_input_price * cache_read_input_tokens / 1000.0
        + cache_write_input_price * cache_write_input_tokens / 1000.0
    )


def get_model_id(
    model: type_model_name,
    enable_cross_region: bool = ENABLE_BEDROCK_CROSS_REGION_INFERENCE,
    bedrock_region: str = BEDROCK_REGION,
) -> str:
    # Ref: https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids-arns.html
    base_model_ids = {
        "claude-v4-opus": "anthropic.claude-opus-4-20250514-v1:0",
        "claude-v4-sonnet": "anthropic.claude-sonnet-4-20250514-v1:0",
        "claude-v3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
        "claude-v3-opus": "anthropic.claude-3-opus-20240229-v1:0",
        "claude-v3.5-sonnet": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "claude-v3.5-sonnet-v2": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "claude-v3.7-sonnet": "anthropic.claude-3-7-sonnet-20250219-v1:0",
        "claude-v3.5-haiku": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "mistral-7b-instruct": "mistral.mistral-7b-instruct-v0:2",
        "mixtral-8x7b-instruct": "mistral.mixtral-8x7b-instruct-v0:1",
        "mistral-large": "mistral.mistral-large-2402-v1:0",
        "mistral-large-2": "mistral.mistral-large-2407-v1:0",
        # New Amazon Nova models
        "amazon-nova-pro": "amazon.nova-pro-v1:0",
        "amazon-nova-lite": "amazon.nova-lite-v1:0",
        "amazon-nova-micro": "amazon.nova-micro-v1:0",
        # Amazon Nova Canvas (image generation)
        "amazon-nova-canvas": "amazon.nova-canvas-v1:0",
        # Amazon Nova Reel (video generation)
        "amazon-nova-reel": "amazon.nova-reel-v1:0",
        # DeepSeek models
        "deepseek-r1": "deepseek.r1-v1:0",
        # Meta Llama 3 models
        "llama3-3-70b-instruct": "meta.llama3-3-70b-instruct-v1:0",
        "llama3-2-1b-instruct": "meta.llama3-2-1b-instruct-v1:0",
        "llama3-2-3b-instruct": "meta.llama3-2-3b-instruct-v1:0",
        "llama3-2-11b-instruct": "meta.llama3-2-11b-instruct-v1:0",
        "llama3-2-90b-instruct": "meta.llama3-2-90b-instruct-v1:0",
    }

    # Made this list by scripts/cross_region_inference/get_supported_cross_region_inferences.py
    # Ref: https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html
    supported_regions = {
        "us-east-1": {
            "area": "us",
            "models": [
                "amazon-nova-lite",
                "amazon-nova-micro",
                "amazon-nova-pro",
                "claude-v4-opus",
                "claude-v4-sonnet",
                "claude-v3-haiku",
                "claude-v3-opus",
                "claude-v3.5-haiku",
                "claude-v3.5-sonnet",
                "claude-v3.5-sonnet-v2",
                "claude-v3.7-sonnet",
                "deepseek-r1",
                "llama3-3-70b-instruct",
                "llama3-2-1b-instruct",
                "llama3-2-3b-instruct",
                "llama3-2-11b-instruct",
                "llama3-2-90b-instruct",
            ],
        },
        "us-east-2": {
            "area": "us",
            "models": [
                "amazon-nova-lite",
                "amazon-nova-micro",
                "amazon-nova-pro",
                "claude-v4-opus",
                "claude-v4-sonnet",
                "claude-v3-haiku",
                "claude-v3.5-haiku",
                "claude-v3.5-sonnet",
                "claude-v3.5-sonnet-v2",
                "claude-v3.7-sonnet",
                "deepseek-r1",
                "llama3-3-70b-instruct",
                "llama3-2-1b-instruct",
                "llama3-2-3b-instruct",
                "llama3-2-11b-instruct",
                "llama3-2-90b-instruct",
            ],
        },
        "us-west-2": {
            "area": "us",
            "models": [
                "amazon-nova-lite",
                "amazon-nova-micro",
                "amazon-nova-pro",
                "claude-v4-opus",
                "claude-v4-sonnet",
                "claude-v3-haiku",
                "claude-v3-opus",
                "claude-v3.5-haiku",
                "claude-v3.5-sonnet",
                "claude-v3.5-sonnet-v2",
                "claude-v3.7-sonnet",
                "deepseek-r1",
                "llama3-3-70b-instruct",
                "llama3-2-1b-instruct",
                "llama3-2-3b-instruct",
                "llama3-2-11b-instruct",
                "llama3-2-90b-instruct",
            ],
        },
        "eu-central-1": {
            "area": "eu",
            "models": [
                "amazon-nova-lite",
                "amazon-nova-micro",
                "amazon-nova-pro",
                "claude-v4-sonnet",
                "claude-v3-haiku",
                "claude-v3.5-sonnet",
                "claude-v3.7-sonnet",
                "llama3-2-1b-instruct",
                "llama3-2-3b-instruct",
            ],
        },
        "eu-west-1": {
            "area": "eu",
            "models": [
                "amazon-nova-lite",
                "amazon-nova-micro",
                "amazon-nova-pro",
                "claude-v4-sonnet",
                "claude-v3-haiku",
                "claude-v3.5-sonnet",
                "claude-v3.7-sonnet",
                "llama3-2-1b-instruct",
                "llama3-2-3b-instruct",
            ],
        },
        "eu-west-2": {"area": "eu", "models": []},
        "eu-west-3": {
            "area": "eu",
            "models": [
                "amazon-nova-lite",
                "amazon-nova-micro",
                "amazon-nova-pro",
                "claude-v4-sonnet",
                "claude-v3-haiku",
                "claude-v3.5-sonnet",
                "claude-v3.7-sonnet",
                "llama3-2-1b-instruct",
                "llama3-2-3b-instruct",
            ],
        },
        "eu-north-1": {
            "area": "eu",
            "models": [
                "amazon-nova-lite",
                "amazon-nova-micro",
                "amazon-nova-pro",
            ],
        },
        "ap-south-1": {
            "area": "apac",
            "models": [
                "amazon-nova-lite",
                "amazon-nova-micro",
                "amazon-nova-pro",
                "claude-v4-sonnet",
                "claude-v3-haiku",
                "claude-v3.5-sonnet",
                "claude-v3.5-sonnet-v2",
            ],
        },
        "ap-northeast-1": {
            "area": "apac",
            "models": [
                "amazon-nova-lite",
                "amazon-nova-micro",
                "amazon-nova-pro",
                "claude-v4-sonnet",
                "claude-v3-haiku",
                "claude-v3.5-sonnet",
                "claude-v3.5-sonnet-v2",
            ],
        },
        "ap-northeast-2": {
            "area": "apac",
            "models": [
                "amazon-nova-lite",
                "amazon-nova-micro",
                "amazon-nova-pro",
                "claude-v4-sonnet",
                "claude-v3-haiku",
                "claude-v3.5-sonnet",
                "claude-v3.5-sonnet-v2",
            ],
        },
        "ap-northeast-3": {"area": "apac", "models": ["claude-v3.5-sonnet-v2"]},
        "ap-southeast-1": {
            "area": "apac",
            "models": [
                "amazon-nova-lite",
                "amazon-nova-micro",
                "amazon-nova-pro",
                "claude-v4-sonnet",
                "claude-v3-haiku",
                "claude-v3.5-sonnet",
                "claude-v3.5-sonnet-v2",
            ],
        },
        "ap-southeast-2": {
            "area": "apac",
            "models": [
                "amazon-nova-lite",
                "amazon-nova-micro",
                "amazon-nova-pro",
                "claude-v4-sonnet",
                "claude-v3-haiku",
                "claude-v3.5-sonnet",
                "claude-v3.5-sonnet-v2",
            ],
        },
    }

    base_model_id = base_model_ids.get(model)
    if not base_model_id:
        raise ValueError(f"Unsupported model: {model}")

    model_id = base_model_id

    if enable_cross_region:
        if (
            bedrock_region in supported_regions
            and model in supported_regions[bedrock_region]["models"]
        ):
            region_prefix = supported_regions[bedrock_region]["area"]
            model_id = f"{region_prefix}.{base_model_id}"
            logger.info(
                f"Using cross-region model ID: {model_id} for model '{model}' in region '{BEDROCK_REGION}'"
            )
        else:
            logger.warning(
                f"Region '{bedrock_region}' does not support cross-region inference for model '{model}'."
            )
    else:
        logger.info(f"Using local model ID: {model_id} for model '{model}'")

    return model_id


@retry(
    exceptions=(BedrockThrottlingException,),
    tries=3,
    delay=60,
    backoff=2,
    jitter=(0, 2),
    logger=logger,
)
def generate_image_with_nova_canvas(
    prompt: str,
    negative_prompt: str | None = None,
    width: int = 1024,
    height: int = 1024,
    cfg_scale: float = 7.0,
    seed: int | None = None,
) -> dict[str, Any]:
    """Generate an image using Amazon Nova Canvas"""
    client = get_bedrock_runtime_client()
    
    # Generate random seed if not provided
    if seed is None:
        seed = random.randint(0, 2147483647)
    
    # Prepare the request body
    request_body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": prompt,
            "images": [],
        },
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "height": height,
            "width": width,
            "cfgScale": cfg_scale,
            "seed": seed,
        }
    }
    
    # Add negative prompt if provided
    if negative_prompt:
        request_body["textToImageParams"]["negativeText"] = negative_prompt
    
    try:
        response = client.invoke_model(
            modelId=get_model_id("amazon-nova-canvas"),
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        response_body = json.loads(response["body"].read())
        
        # Extract the generated image
        if "images" in response_body and len(response_body["images"]) > 0:
            image_data = response_body["images"][0]
            return {
                "image_data": base64.b64decode(image_data),
                "seed": seed,
                "prompt": prompt,
            }
        else:
            raise ValueError("No image generated in response")
            
    except ClientError as e:
        if e.response["Error"]["Code"] == "ThrottlingException":
            raise BedrockThrottlingException(
                "Bedrock API is throttling requests"
            ) from e
        raise


@retry(
    exceptions=(BedrockThrottlingException,),
    tries=3,
    delay=60,
    backoff=2,
    jitter=(0, 2),
    logger=logger,
)
def generate_video_with_nova_reel(
    prompt: str,
    negative_prompt: str | None = None,
    duration_seconds: int = 6,
    fps: int = 24,
    seed: int | None = None,
) -> dict[str, Any]:
    """Generate a video using Amazon Nova Reel"""
    client = get_bedrock_runtime_client()
    
    # Generate random seed if not provided
    if seed is None:
        seed = random.randint(0, 2147483647)
    
    # Ensure duration is within limits (max 6 seconds)
    duration_seconds = min(duration_seconds, 6)
    
    # Prepare the request body
    request_body = {
        "taskType": "TEXT_VIDEO",
        "textToVideoParams": {
            "text": prompt,
        },
        "videoGenerationConfig": {
            "durationSeconds": duration_seconds,
            "fps": fps,
            "dimension": "1280x720",  # Standard HD resolution
            "seed": seed,
        }
    }
    
    # Add negative prompt if provided
    if negative_prompt:
        request_body["textToVideoParams"]["negativeText"] = negative_prompt
    
    try:
        response = client.invoke_model(
            modelId=get_model_id("amazon-nova-reel"),
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        response_body = json.loads(response["body"].read())
        
        # Extract the generated video
        if "videos" in response_body and len(response_body["videos"]) > 0:
            video_data = response_body["videos"][0]
            return {
                "video_data": base64.b64decode(video_data),
                "seed": seed,
                "prompt": prompt,
                "duration_seconds": duration_seconds,
            }
        else:
            raise ValueError("No video generated in response")
            
    except ClientError as e:
        if e.response["Error"]["Code"] == "ThrottlingException":
            raise BedrockThrottlingException(
                "Bedrock API is throttling requests"
            ) from e
        raise


def calculate_media_generation_price(
    model: type_model_name,
    region: str = BEDROCK_REGION,
) -> float:
    """Calculate price for media generation (per image or video)"""
    return (
        BEDROCK_PRICING.get(region, {})
        .get(model, {})
        .get("output", BEDROCK_PRICING["default"][model]["output"])
    )