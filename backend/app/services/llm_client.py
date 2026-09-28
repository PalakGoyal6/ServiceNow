import re
import json
import httpx
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError
from backend.app.config import settings

T = TypeVar("T", bound=BaseModel)


class LLMClientError(Exception):
    pass


def extract_json_str(text: str) -> str:
    """
    Strips markdown code blocks and finds the JSON payload.
    """
    text = text.strip()
    # Remove markdown code blocks if present
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()
    return text


def _call_openai_compatible(
    endpoint: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model or "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
    }
    with httpx.Client(timeout=20.0) as client:
        response = client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def _call_anthropic(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model or "claude-3-5-sonnet-20241022",
        "max_tokens": 2048,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
    }
    with httpx.Client(timeout=20.0) as client:
        response = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


def _call_gemini(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    model_name = model or "gemini-1.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "response_mime_type": "application/json",
        },
    }
    with httpx.Client(timeout=20.0) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


def complete_raw(system_prompt: str, user_prompt: str) -> str:
    provider = (settings.LLM_PROVIDER or "none").lower()
    api_key = settings.Y
    model = settings.LLM_MODEL

    if provider == "none" or not api_key:
        raise LLMClientError("LLM provider is set to 'none' or missing API key. Fallback will be used.")

    if provider == "openai":
        return _call_openai_compatible("https://api.openai.com/v1/chat/completions", api_key, model, system_prompt, user_prompt)
    elif provider == "anthropic":
        return _call_anthropic(api_key, model, system_prompt, user_prompt)
    elif provider == "gemini":
        return _call_gemini(api_key, model, system_prompt, user_prompt)
    else:
        raise LLMClientError(f"Unsupported LLM provider: {provider}")


def complete_json(system_prompt: str, user_prompt: str, schema: Type[T]) -> T:
    """
    Calls the configured LLM, extracts JSON, validates against schema.
    Retries once on validation failure with the validation error feedback.
    Raises LLMClientError on failure.
    """
    json_instruction = f"\nYou must output strictly valid raw JSON conforming to this schema:\n{json.dumps(schema.model_json_schema())}\nDo not include any commentary or preamble outside the JSON."
    full_system = system_prompt + json_instruction

    try:
        raw_text = complete_raw(full_system, user_prompt)
        clean_json = extract_json_str(raw_text)
        return schema.model_validate_json(clean_json)
    except (ValidationError, json.JSONDecodeError) as e:
        # Retry once with error feedback
        retry_prompt = f"{user_prompt}\n\n[Previous attempt failed with validation error: {str(e)}]. Please fix and return ONLY valid JSON matching the schema."
        try:
            raw_text = complete_raw(full_system, retry_prompt)
            clean_json = extract_json_str(raw_text)
            return schema.model_validate_json(clean_json)
        except Exception as retry_err:
            raise LLMClientError(f"Failed to parse LLM JSON after retry: {retry_err}")
    except Exception as e:
        raise LLMClientError(f"LLM call failed: {e}")
