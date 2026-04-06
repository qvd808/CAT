import pytest
import json
from pydantic import BaseModel
from utils.parsing import parse_llm_json

class CriticOutput(BaseModel):
    approved: bool
    strengths: list[str]

class TestEngineerOutput(BaseModel):
    test_cases: list[dict]
    test_file_path: str

def test_parse_clean_json():
    text = '{"approved": true, "strengths": ["good architecture"]}'
    res = parse_llm_json(text, CriticOutput)
    assert res["approved"] is True

def test_parse_markdown_json_complete():
    text = '''```json
{
    "approved": true,
    "strengths": ["good"]
}
```'''
    res = parse_llm_json(text, CriticOutput)
    assert res["approved"] is True

def test_parse_markdown_missing_closing_tick():
    # The LLM gets cut off before finishing the markdown ticks 
    text = '''```json
{
    "approved": true,
    "strengths": ["good design", "nice tech stack"'''
    res = parse_llm_json(text, CriticOutput)
    assert res["approved"] is True
    assert len(res["strengths"]) == 2

def test_parse_markdown_no_language_missing_closing_tick():
    # Like the Design Critic failure: opening tag ``` without json, and cut off
    text = '''```
{
    "approved": true,
    "strengths": [
        "The design covers all original requirements",
        "The architecture and tech stack are well-aligned"'''
    res = parse_llm_json(text, CriticOutput)
    assert res["approved"] is True
    assert len(res["strengths"]) == 2

def test_parse_unescaped_quotes_in_code():
    # Like Test Engineer creating code with unescaped quotes
    text = '''```json
{
    "test_cases": [
        {
            "name": "test_app",
            "description": "tests the app",
            "code": "fn main() { println!("Hello \\"World\\""); }"
        }
    ],
    "test_file_path": "tests/main.rs"
}
```'''
    res = parse_llm_json(text, TestEngineerOutput)
    assert len(res["test_cases"]) == 1
    assert "println!(" in res["test_cases"][0]["code"]

def test_parse_no_markdown_but_cut_off():
    # Just raw JSON cut off
    text = '''{
    "approved": false,
    "strengths": ["fast'''
    res = parse_llm_json(text, CriticOutput)
    assert res["approved"] is False

def test_parse_pydantic_validation_failure():
    # If json_repair repairs completely but the structure is missing required fields,
    # it must raise ValueError indicating Pydantic validation failed, NOT simple parsing error.
    text = '''```json
{
    "test_cases": [
        {
            "name": "test_add_todo",
            "description": "Test adding a new todo item",
            "code": "#[cfg(test)]\\nmod tests {\\n    use super::*;\\n\\n    #[test]\\n    fn test_add_todo() {\\n        let conn = init_db();\\n        let result = add_todo(\\"Test todo\\").unwrap();\\n        assert_eq!(result, \\"Todo added!\\");\\n    }\\n}"
        }
    ]
}
```'''
    # Missing test_file_path!
    with pytest.raises(ValueError) as excinfo:
        parse_llm_json(text, TestEngineerOutput)
        
    assert "JSON parsed successfully but failed Pydantic validation" in str(excinfo.value)

