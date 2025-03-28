# src/reposcribe/core.py

import os
import sys
import pathspec  # For gitignore parsing
from typing import List, Tuple


# --- Default Ignore Patterns ---
# Comprehensive list covering common lock files, build artifacts, logs, env files, IDE folders, OS files, media, etc.
DEFAULT_IGNORE_PATTERNS = [
    # Version Control System specific
    ".git/",
    ".hg/",
    ".svn/",
    ".bzr/",
    # User's gitignore file itself (we read it, but don't include its content)
    ".gitignore",
    # Dependency lock files
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "composer.lock",
    "Gemfile.lock",
    "Cargo.lock",
    "go.sum",
    # Compiled code/binaries
    "*.pyc",
    "__pycache__/",
    "*.class",
    "*.jar",
    "*.war",
    "*.ear",
    "*.o",
    "*.a",
    "*.so",
    "*.dylib",
    "*.dll",
    "*.exe",
    "*.wasm",
    "*.elc",
    # Common build output directories
    "build/",
    "dist/",
    "target/",
    "bin/",
    "obj/",
    "out/",
    "public/build/",  # Common in web frameworks
    # Framework/Tool specific build/cache outputs
    ".next/",
    ".nuxt/",
    ".svelte-kit/",
    ".vercel/",
    ".serverless/",
    ".terraform/",
    # Environment files
    ".env",
    ".env.*",
    # Virtual environments
    ".venv/",
    "venv/",
    "env/",
    ".env/",
    # IDE/Editor configuration
    ".idea/",
    ".vscode/",
    "*.sublime-*",
    ".project",
    ".settings/",
    ".classpath",  # Eclipse
    "*.swp",
    "*.swo",  # Vim
    # OS generated files
    ".DS_Store",
    "Thumbs.db",
    # Log files
    "*.log",
    # Test & Coverage output
    "coverage/",
    ".coverage",
    "htmlcov/",
    "*.lcov",
    "nosetests.xml",  # Common test report names
    "pytest.xml",
    ".pytest_cache/",
    # Large Media/Assets (generally not code/text)
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.bmp",
    "*.tiff",
    "*.webp",
    "*.ico",
    "*.svg",  # Can sometimes be code-like, but often large/design assets
    "*.mp3",
    "*.wav",
    "*.ogg",
    "*.flac",
    "*.mp4",
    "*.avi",
    "*.mov",
    "*.wmv",
    "*.mkv",
    "*.webm",
    "*.pdf",
    "*.doc",
    "*.docx",
    "*.ppt",
    "*.pptx",
    "*.xls",
    "*.xlsx",
    "*.odt",
    "*.odp",
    "*.ods",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.rar",
    "*.7z",
    "*.tgz",
    "*.bz2",
    "*.iso",
    "*.dmg",
    "*.ttf",
    "*.otf",
    "*.woff",
    "*.woff2",  # Fonts
    # Dependency directories (often huge and specified in .gitignore anyway, but good defaults)
    "node_modules/",
    "vendor/",
    "bower_components/",
    # Cloud formation / Deployment artifacts
    "cdk.out/",
]

# --- Gitignore Reading ---


def read_gitignore_lines(gitignore_path: str) -> List[str]:
    """
    Reads .gitignore patterns, combining them with built-in default ignores.
    User patterns are appended, allowing them to potentially override defaults via negation.
    """
    # Start with a copy of the default patterns
    lines = DEFAULT_IGNORE_PATTERNS.copy()
    added_user_patterns = False

    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                user_lines = [
                    line
                    for line in f.read().splitlines()
                    if line.strip() and not line.strip().startswith("#")
                ]
                if user_lines:
                    lines.extend(user_lines)
                    added_user_patterns = True
            if added_user_patterns:
                print(
                    f"Read and appended patterns from user .gitignore: {gitignore_path}",
                    file=sys.stderr,
                )
            else:
                print(
                    f"User .gitignore exists but is empty or only comments: {gitignore_path}",
                    file=sys.stderr,
                )

        except Exception as e:
            print(
                f"Warning: Could not read user .gitignore {gitignore_path}: {e}",
                file=sys.stderr,
            )
            print("Continuing with default ignore patterns only.", file=sys.stderr)
    else:
        print(
            "No user .gitignore file found. Using default ignore patterns only.",
            file=sys.stderr,
        )

    # print(f"Final patterns being used: {lines}", file=sys.stderr) # Uncomment for debugging
    return lines


def generate_file_tree(file_paths: List[str]) -> str:
    """Generates a string representation of a file tree from a list of paths."""
    if not file_paths:
        return "(No files found to include in tree)\n"

    tree_lines = ["Exported File Structure:", "."]
    structure = {}  # Using a dict to represent the file tree structure

    # Build nested dictionary structure from paths
    for (
        path_str
    ) in (
        file_paths
    ):  # Assumes paths are sorted beforehand if needed, though order doesn't strictly matter for dict building
        parts = path_str.split("/")
        current_level = structure
        for i, part in enumerate(parts):
            if i == len(parts) - 1:  # It's a file (leaf node)
                current_level[part] = (
                    None  # Use None to indicate a file vs. a directory dict
                )
            else:  # It's a directory
                if part not in current_level:
                    current_level[part] = {}  # Create dir if not exists
                if current_level[part] is None:  # Handle edge case file/dir conflict
                    print(
                        f"Warning: Path conflict converting file to directory for tree structure near '{path_str}'",
                        file=sys.stderr,
                    )
                    current_level[part] = {}
                current_level = current_level[part]

    # Recursive helper function to format the tree lines
    def format_level(level_dict, current_indent="", is_last_level=True):
        items = sorted(level_dict.keys())
        for i, name in enumerate(items):
            is_last_item = i == len(items) - 1
            connector = "└── " if is_last_item else "├── "
            tree_lines.append(f"{current_indent}{connector}{name}")

            if isinstance(level_dict[name], dict):  # If it's a directory, recurse
                next_indent = current_indent + ("    " if is_last_item else "│   ")
                format_level(level_dict[name], next_indent, is_last_level=is_last_item)

    format_level(structure)
    return "\n".join(tree_lines) + "\n"


# --- File Discovery ---


def find_exportable_files(project_root: str, spec: pathspec.PathSpec) -> List[str]:
    """
    Walks the directory, applies gitignore rules using PathSpec,
    and returns a sorted list of relative file paths (using '/') to export.
    """
    exportable_files = []

    # os.walk generates paths relative to the starting directory (project_root)
    for dirpath, dirnames, filenames in os.walk(project_root, topdown=True):

        # --- Pruning Ignored Directories (Efficiency) ---
        # Get relative path of the current directory being walked
        current_rel_dir = os.path.relpath(dirpath, project_root)
        if current_rel_dir == ".":
            current_rel_dir = ""  # Use empty string for root relative path consistency

        dirs_to_prune = set()
        for d in dirnames:
            # Construct relative path for the directory *using '/' separators*
            # Add trailing slash for pathspec directory matching
            dir_rel_path_for_spec = (
                os.path.join(current_rel_dir, d).replace(os.sep, "/") + "/"
            )
            if spec.match_file(dir_rel_path_for_spec):
                dirs_to_prune.add(d)

        # Modify dirnames *in place* using slice assignment to prevent os.walk
        # from descending into directories in the prune set.
        if dirs_to_prune:
            # Keep only directories NOT in the prune set
            dirnames[:] = [d for d in dirnames if d not in dirs_to_prune]
        # --- End Pruning ---

        # Process files in the current (non-pruned) directory
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            # Get relative path using '/' separator for pathspec matching and output consistency
            relative_path = os.path.relpath(full_path, project_root).replace(
                os.sep, "/"
            )

            # Check if the file itself is ignored by pathspec rules
            if not spec.match_file(relative_path):
                exportable_files.append(relative_path)

    return sorted(exportable_files)


# --- Output File Writing ---


def write_export_file(
    output_file_path: str,
    project_root: str,
    files_to_export: List[str],
    encoding: str,
    errors: str,
    include_tree: bool,
) -> Tuple[int, int]:
    """
    Writes the file tree (optional) and content of the specified files
    to the output file, returning (file_count, total_size).
    """
    file_count = 0
    total_size = 0
    try:
        with open(output_file_path, "w", encoding=encoding) as outfile:

            # --- Add File Tree (Optional) ---
            if include_tree:
                tree_string = generate_file_tree(files_to_export)
                outfile.write("--- START FILE TREE ---\n")
                outfile.write(tree_string)
                outfile.write("--- END FILE TREE ---\n\n")
            # --- End File Tree ---

            # --- Add File Contents ---
            for relative_path in files_to_export:
                # Construct full path using OS-specific separator
                full_path = os.path.join(
                    project_root, relative_path.replace("/", os.sep)
                )
                print(
                    f"  Scribing: {relative_path}", file=sys.stderr
                )  # Log progress to stderr

                # Write file header using POSIX-style path for consistency
                outfile.write(f"--- START FILE: {relative_path} ---\n")
                try:
                    # Attempt to read the file content
                    with open(
                        full_path, "r", encoding=encoding, errors=errors
                    ) as infile:
                        content = infile.read()
                        outfile.write(content)
                        file_count += 1
                        # Estimate size based on encoded content length
                        # Use default 'utf-8' for size calculation if encoding fails? Or skip? Let's use specified encoding.
                        try:
                            total_size += len(content.encode(encoding, errors=errors))
                        except Exception:
                            # If encoding the read content fails even with 'errors', skip size calc for this file
                            print(
                                f"Warning: Could not encode content for size calculation for file {relative_path}",
                                file=sys.stderr,
                            )

                except Exception as e:
                    # Handles file read errors (permissions, binary issues if 'strict', etc.)
                    error_msg = f"Error reading file: {e}"
                    outfile.write(f"{error_msg}\n")
                    print(
                        f"Warning: Could not read file {relative_path}: {e}",
                        file=sys.stderr,
                    )

                # Write file footer
                outfile.write(f"\n--- END FILE: {relative_path} ---\n\n")

    except Exception as e:
        # Handle errors during output file opening/writing
        print(
            f"\nAn error occurred during writing export file '{output_file_path}': {e}",
            file=sys.stderr,
        )
        # Re-raise the exception to be caught by the CLI for proper exit code
        raise e

    return file_count, total_size
