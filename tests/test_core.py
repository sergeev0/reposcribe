import os
import pytest
import pathspec
from pathlib import Path
import sys

# Functions to test
from reposcribe.core import (
    read_gitignore_lines,
    generate_file_tree,  # Manual version
    find_exportable_files,
    write_export_file,
)


# --- Helper to create mock file system ---
# (Still necessary for find/write tests)
def create_mock_fs(base_path: Path, structure: dict, gitignore_content: str = None):
    """Creates a mock file system structure under base_path."""
    if gitignore_content is not None:
        (base_path / ".gitignore").write_text(gitignore_content, encoding="utf-8")
    # Always create a .git directory
    git_dir = base_path / ".git"
    if not git_dir.exists():
        git_dir.mkdir()
        (git_dir / "config").write_text("git stuff", encoding="utf-8")
    # Create files/dirs
    for name, content in structure.items():
        path = base_path / name
        if isinstance(content, dict):
            if not path.exists():
                path.mkdir()
            create_mock_fs(path, content)
        elif isinstance(content, str):
            path.write_text(content, encoding="utf-8")


# --- Test .gitignore Reading ---


def test_read_gitignore_lines_with_content(tmp_path):
    content = "# Comment\n*.log\n\nbuild/"
    gitignore_path = tmp_path / ".gitignore"
    gitignore_path.write_text(content, encoding="utf-8")
    lines = read_gitignore_lines(str(gitignore_path))

    # Check that the test-specific patterns AND defaults are present
    # It's easier to check for the presence of specific important ones
    # rather than comparing the entire potentially huge default list.
    assert "*.log" in lines
    assert "build/" in lines
    assert ".git/" in lines  # Default
    assert ".gitignore" in lines  # Default
    assert ".env" in lines  # Default
    assert "*.pyc" in lines  # Default
    assert "*.png" in lines  # Default
    assert "node_modules/" in lines  # Default


# --- Test Tree Generation (Manual) ---
def test_generate_file_tree_empty():  # Remains the same
    assert generate_file_tree([]) == "(No files found to include in tree)\n"


def test_generate_file_tree_simple():
    files = ["README.md", "src/app.py"]
    # Expected output from the MANUAL tree function
    expected_tree = """Exported File Structure:
.
├── README.md
└── src
    └── app.py
"""
    assert generate_file_tree(sorted(files)) == expected_tree


# --- Test File Finding ---


def test_find_files_basic_ignore(tmp_path):
    structure = {
        "main.py": "print('hello')",
        "README.md": "# Project",
        "app.log": "Log message",  # Ignored by *.log (user or default)
        ".env": "SECRET=123",  # Ignored by default .env
        "image.png": "imgdata",  # Ignored by default *.png
        "build": {"output.bin": ""},  # Ignored by build/ (user or default)
        "src": {"module.py": "code"},
    }
    gitignore = "*.log\nbuild/"  # User rules
    create_mock_fs(tmp_path, structure, gitignore)
    spec = pathspec.PathSpec.from_lines(
        pathspec.patterns.GitWildMatchPattern,
        read_gitignore_lines(str(tmp_path / ".gitignore")),
    )
    found_files = find_exportable_files(str(tmp_path), spec)
    # .gitignore, .env, *.log, build/, *.png should all be ignored now
    expected_files = ["README.md", "main.py", "src/module.py"]
    assert sorted(found_files) == sorted(expected_files)


# --- Test File Writing ---


def test_write_export_file_with_tree(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    output_file = tmp_path / "output.txt"
    files_structure = {"file1.txt": "Content1.", "subdir": {"file2.py": "# Code"}}
    create_mock_fs(project_root, files_structure)
    files_to_export = sorted(["file1.txt", "subdir/file2.py"])
    encoding = "utf-8"
    errors = "ignore"

    file_count, total_size = write_export_file(
        str(output_file),
        str(project_root),
        files_to_export,
        encoding,
        errors,
        include_tree=True,
    )
    assert output_file.exists()
    assert file_count == 2

    content = output_file.read_text(encoding=encoding)
    # Check tree presence
    assert "--- START FILE TREE ---" in content
    assert "Exported File Structure:" in content
    # Check specific tree lines with correct connectors
    assert "├── file1.txt" in content  # <-- Changed from '└──'
    assert "└── subdir" in content  # Check directory part
    assert "    └── file2.py" in content  # Check nested file part
    assert "--- END FILE TREE ---" in content
    # Check file content presence
    assert "--- START FILE: file1.txt ---" in content
    assert "Content1." in content
    assert "--- START FILE: subdir/file2.py ---" in content
    assert "# Code" in content


def test_write_export_file_source_missing(tmp_path):
    """Test writing when a source file in the list is missing."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    output_file = tmp_path / "output.txt"
    files_structure = {"real.txt": "Exists."}
    create_mock_fs(project_root, files_structure)
    files_to_export = ["real.txt", "missing.txt"]  # missing.txt doesn't exist
    encoding = "utf-8"
    errors = "ignore"

    # Call without tree for simplicity in checking output
    file_count, total_size = write_export_file(
        str(output_file),
        str(project_root),
        files_to_export,
        encoding,
        errors,
        include_tree=False,
    )
    assert output_file.exists()
    assert file_count == 1  # Only one file successfully read

    content = output_file.read_text(encoding=encoding)
    # Check content for existing file
    assert "--- START FILE: real.txt ---" in content
    assert "Exists." in content
    # Check content for missing file contains error
    assert "--- START FILE: missing.txt ---" in content
    assert "Error reading file:" in content  # Generic check for error message
