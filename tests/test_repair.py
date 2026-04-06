import json_repair

def test_json_repair_truncation():
    text = """```json
{
    "readme": "# Tauri Todo",
    "files": [
        {
            "path": "test.txt",
            "content": "abc"
"""
    result = json_repair.repair_json(text, return_objects=True)
    assert isinstance(result, dict)
    assert "readme" in result
