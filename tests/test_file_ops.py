
import os
import shutil
import pytest
from unittest.mock import patch
from graph.nodes.prototype_builder import _write_files

def test_write_files_cleans_directory(tmp_path):
    project_name = "CleanTest"
    test_output_root = tmp_path / "output"
    os.makedirs(test_output_root, exist_ok=True)
    
    with patch("graph.nodes.prototype_builder.OUTPUT_DIR", str(test_output_root)):
        project_dir = test_output_root / project_name
        os.makedirs(project_dir, exist_ok=True)
        
        # 1. Create a "zombie" file
        zombie_path = project_dir / "zombie.txt"
        zombie_path.write_text("i should be deleted")
        
        assert zombie_path.exists()
        
        # 2. Run _write_files with a different set of files
        files = [{"path": "main.py", "content": "print('hello')", "description": "test"}]
        _write_files(project_name, files, "# Readme")
        
        # 3. Verify zombie is gone
        assert not zombie_path.exists()
        assert (project_dir / "main.py").exists()

def test_write_files_creates_nested_dirs(tmp_path):
    test_output_root = tmp_path / "output_nested"
    os.makedirs(test_output_root, exist_ok=True)
    
    with patch("graph.nodes.prototype_builder.OUTPUT_DIR", str(test_output_root)):
        files = [{"path": "src/deep/nested/file.txt", "content": "data", "description": "test"}]
        _write_files("NestedProject", files, "# Readme")
        
        file_path = test_output_root / "NestedProject" / "src" / "deep" / "nested" / "file.txt"
        assert file_path.exists()
