"""
Shared utilities for parsing LLM responses into structured data.
Handles common LLM output quirks: markdown blocks, trailing text, broken JSON, etc.
"""

import json
import re
from pydantic import BaseModel


def parse_llm_json(text: str, model_class: type[BaseModel] | None = None) -> dict:
    """
    Robustly extract and parse JSON from an LLM response.
    
    Handles:
    - ```json ... ``` code blocks
    - ``` ... ``` code blocks  
    - JSON with leading/trailing text
    - JSON with trailing commas
    - JSON with single quotes (converts to double)
    - Multiple JSON blocks (takes the first valid one)
    
    Args:
        text: Raw LLM response text
        model_class: Optional Pydantic model to validate against
        
    Returns:
        Parsed dict (validated against model_class if provided)
    """
    text = text.strip()
    last_val_error = None
    
    def try_strategy(candidate: str):
        nonlocal last_val_error
        result, err = _try_parse(candidate, model_class)
        if err and not last_val_error:
            last_val_error = err
        return result
    
    # Strategy 1: Extract from ```json block
    json_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_block_match:
        candidate = json_block_match.group(1).strip()
        result = try_strategy(candidate)
        if result is not None:
            return result

    # Strategy 2: Extract from ``` block
    code_block_match = re.search(r'```\s*([\s\S]*?)\s*```', text)
    if code_block_match:
        candidate = code_block_match.group(1).strip()
        result = try_strategy(candidate)
        if result is not None:
            return result

    # Strategy 3: Find JSON object directly — look for { ... }
    brace_match = re.search(r'\{[\s\S]*\}', text)
    if brace_match:
        candidate = brace_match.group(0).strip()
        result = try_strategy(candidate)
        if result is not None:
            return result

    # Strategy 4: Try the whole text as-is
    result = try_strategy(text)
    if result is not None:
        return result

    # Strategy 5: Try fixing common JSON issues
    cleaned = _fix_common_json_issues(text)
    brace_match = re.search(r'\{[\s\S]*\}', cleaned)
    if brace_match:
        result = try_strategy(brace_match.group(0))
        if result is not None:
            return result

    # Strategy 6: Escape code strings and retry
    escaped = _escape_code_strings_in_json(text)
    brace_match = re.search(r'\{[\s\S]*\}', escaped)
    if brace_match:
        result = try_strategy(brace_match.group(0))
        if result is not None:
            return result

    # All strategies failed
    if last_val_error:
        raise ValueError(f"JSON parsed successfully but failed Pydantic validation: {str(last_val_error)}")
    raise ValueError(f"Could not parse JSON from LLM response. First 300 chars: {text[:300]}")


def _try_parse(text: str, model_class: type[BaseModel] | None = None) -> tuple[dict | None, Exception | None]:
    """Try to parse text as JSON and optionally validate with Pydantic."""
    last_val_error = None

    # Strategy A: standard json.loads — most faithful, handles escape sequences correctly
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            if model_class:
                from pydantic import ValidationError
                try:
                    validated = model_class.model_validate(data)
                    return validated.model_dump(), None
                except ValidationError as e:
                    last_val_error = e
            else:
                return data, None
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy B: json_repair for malformed JSON (trailing commas, single quotes, etc.)
    try:
        import json_repair
        data = json_repair.repair_json(text, return_objects=True)
        if not isinstance(data, dict):
            return None, last_val_error
        if model_class:
            from pydantic import ValidationError
            try:
                validated = model_class.model_validate(data)
                return validated.model_dump(), None
            except ValidationError as e:
                return None, e
        return data, None
    except Exception as e:
        from pydantic import ValidationError
        if isinstance(e, ValidationError):
            return None, e
        return None, last_val_error


def _escape_code_strings_in_json(text: str) -> str:
    """
    Fix unescaped newlines and quotes inside JSON string values.
    Uses a proper state machine to track when we're inside a string.
    """
    result = []
    i = 0
    in_string = False
    escape_next = False
    
    while i < len(text):
        char = text[i]
        
        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue
            
        if char == '\\':
            result.append(char)
            escape_next = True
            i += 1
            continue
        
        if char == '"':
            in_string = not in_string
            result.append(char)
            i += 1
            continue
        
        if in_string:
            if char == '\n':
                result.append('\\n')
                i += 1
                continue
            elif char == '\r':
                result.append('\\r')
                i += 1
                continue
            elif char == '\t':
                result.append('\\t')
                i += 1
                continue
        
        result.append(char)
        i += 1
    
    return ''.join(result)


def _fix_common_json_issues(text: str) -> str:
    """Fix common JSON formatting issues from LLMs."""
    text = re.sub(r',\s*([}\]])', r'\1', text)
    if '"' not in text and "'" in text:
        text = text.replace("'", '"')
    text = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
    return text