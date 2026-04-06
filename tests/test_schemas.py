import pytest
from utils.parsing import parse_llm_json
from models.schemas import (
    ProductSpec,
    ArchitectureDesign,
    TechStack,
    CritiqueResult,
    PrototypeOutput,
    PrototypePatchOutput,
    TestEngineerOutput,
    QAResult,
    DebuggerVerdict
)

def test_parse_product_spec():
    json_text = """```json
    {
        "project_name": "TestProject",
        "summary": "A cool project summary.",
        "features": ["feature A", "feature B"],
        "user_stories": [
            {
                "title": "Story 1",
                "description": "As a user, I want A, so that B",
                "acceptance_criteria": ["It works"]
            }
        ],
        "constraints": ["No db"],
        "out_of_scope": ["OAuth"]
    }
    ```"""
    res = parse_llm_json(json_text, ProductSpec)
    assert res["project_name"] == "TestProject"
    assert len(res["user_stories"]) == 1

def test_parse_architecture_design():
    json_text = """```json
    {
        "overview": "Simple arch",
        "components": [
            {
                "name": "Backend",
                "responsibility": "Serves API",
                "interfaces": ["REST"]
            }
        ],
        "data_flow": "graph TD\\nA-->B",
        "data_models": ["User", "Post"],
        "api_endpoints": ["/api/v1/users"]
    }
    ```"""
    res = parse_llm_json(json_text, ArchitectureDesign)
    assert res["overview"] == "Simple arch"
    assert len(res["components"]) == 1

def test_parse_tech_stack():
    json_text = """```json
    {
        "recommendations": [
            {
                "category": "Frontend",
                "technology": "React",
                "justification": "Very popular"
            }
        ],
        "infrastructure": "AWS",

        "rationale": "React is good"
    }
    ```"""
    res = parse_llm_json(json_text, TechStack)


def test_parse_critique_result():
    json_text = """```json
    {
        "approved": true,
        "strengths": ["Solid choice"],
        "issues": [],
        "suggestions": ["Add CI"],
        "target_agent": ""
    }
    ```"""
    res = parse_llm_json(json_text, CritiqueResult)
    assert res["approved"] is True

def test_parse_prototype_output():
    json_text = """```json
    {
        "readme": "# Setup\\nRun tests",
        "files": [
            {
                "path": "test.txt",
                "content": "hello world",
                "description": "text file"
            }
        ]
    }
    ```"""
    res = parse_llm_json(json_text, PrototypeOutput)
    assert "setup" in res["readme"].lower()
    assert len(res["files"]) == 1

def test_parse_prototype_patch_output():
    json_text = """```json
    {
        "files": [
            {
                "path": "test.txt",
                "content": "patched content",
                "description": "text file updated"
            }
        ],
        "deleted_paths": ["old_file.txt", "src/removed.js"]
    }
    ```"""
    res = parse_llm_json(json_text, PrototypePatchOutput)
    assert len(res["files"]) == 1
    assert len(res["deleted_paths"]) == 2
    assert "old_file.txt" in res["deleted_paths"]

def test_parse_test_engineer_output():
    json_text = """```json
    {
        "test_cases": [
            {
                "name": "test_hello",
                "description": "tests the text",
                "code": "assert text == 'hello'"
            }
        ],
        "test_file_path": "tests/test_main.py"
    }
    ```"""
    res = parse_llm_json(json_text, TestEngineerOutput)
    assert len(res["test_cases"]) == 1
    assert res["test_file_path"] == "tests/test_main.py"

def test_parse_qa_result():
    json_text = """```json
    {
        "approved": false,
        "requirement_checks": [
            {
                "requirement": "must save data",
                "covered": false,
                "evidence": "missing DB"
            }
        ],
        "test_cases": [],
        "issues": ["DB missing"],
        "test_file_path": "tests/test_main.py"
    }
    ```"""
    res = parse_llm_json(json_text, QAResult)
    assert res["approved"] is False

def test_parse_debugger_verdict():
    json_text = """```json
    {
        "failure_category": "implementation",
        "escalation_target": "builder",
        "affected_files": ["src/main.rs"],
        "root_cause": "Missing semi-colon",
        "patch_hint": "Add semi-colon",
        "architecture_concern": "",
        "debug_iteration": 2
    }
    ```"""
    res = parse_llm_json(json_text, DebuggerVerdict)
    assert res["escalation_target"] == "builder"
    assert res["debug_iteration"] == 2
