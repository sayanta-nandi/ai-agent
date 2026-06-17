"""Tests for file tools implementation."""

from __future__ import annotations

import pytest
from pathlib import Path
import tempfile
import os

from agent_tui.tools import (
    ListFilesTool,
    ReadFileTool,
    WriteFileTool,
    EditFileTool,
    DeleteFileTool,
    ToolResult,
    ToolError,
)
from agent_tui.safety import WorkspaceSafetyError


@pytest.fixture
def temp_workspace() -> Path:
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        # Create some test files and directories
        (workspace / "file1.txt").write_text("File 1 content")
        (workspace / "file2.md").write_text("# File 2\nMarkdown content")

        subdir = workspace / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("Nested file")

        deepdir = subdir / "deep"
        deepdir.mkdir()
        (deepdir / "deep.txt").write_text("Deep file")

        yield workspace


class TestListFilesTool:
    """Tests for ListFilesTool."""

    @pytest.mark.asyncio
    async def test_list_files_root(self, temp_workspace: Path) -> None:
        """Test listing files at workspace root with max_depth=1."""
        tool = ListFilesTool(temp_workspace)
        result = await tool.execute(path=".", max_depth=1)

        assert isinstance(result, ToolResult)
        assert "file1.txt" in result.content
        assert "file2.md" in result.content
        assert "subdir/" in result.content
        assert result.metadata["item_count"] == 3

    @pytest.mark.asyncio
    async def test_list_files_subdir(self, temp_workspace: Path) -> None:
        """Test listing files in a subdirectory."""
        tool = ListFilesTool(temp_workspace)
        result = await tool.execute(path="subdir", max_depth=1)

        assert isinstance(result, ToolResult)
        assert "nested.txt" in result.content
        assert "deep/" in result.content

    @pytest.mark.asyncio
    async def test_list_files_depth_2(self, temp_workspace: Path) -> None:
        """Test listing files with max_depth=2."""
        tool = ListFilesTool(temp_workspace)
        result = await tool.execute(path=".", max_depth=2)

        assert isinstance(result, ToolResult)
        # Should include nested.txt from subdir (level 1)
        assert "nested.txt" in result.content
        # Should include deep/ directory but not its contents (deep/ is level 2)
        assert "deep/" in result.content
        assert "deep.txt" not in result.content  # Would be level 3

    @pytest.mark.asyncio
    async def test_list_files_nonexistent_path(self, temp_workspace: Path) -> None:
        """Test listing a nonexistent path."""
        tool = ListFilesTool(temp_workspace)
        result = await tool.execute(path="nonexistent")

        assert isinstance(result, ToolError)
        assert result.error_type == "not_found"
        assert "does not exist" in result.error_message

    @pytest.mark.asyncio
    async def test_list_files_path_traversal_rejected(self, temp_workspace: Path) -> None:
        """Test that path traversal is rejected."""
        tool = ListFilesTool(temp_workspace)
        result = await tool.execute(path="../outside")

        assert isinstance(result, ToolError)
        assert result.error_type == "validation"

    @pytest.mark.asyncio
    async def test_list_files_invalid_max_depth(self, temp_workspace: Path) -> None:
        """Test that invalid max_depth is rejected."""
        tool = ListFilesTool(temp_workspace)
        result = await tool.execute(path=".", max_depth=0)

        assert isinstance(result, ToolError)
        assert result.error_type == "validation"
        assert "max_depth must be at least 1" in result.error_message

    @pytest.mark.asyncio
    async def test_list_files_on_file_fails(self, temp_workspace: Path) -> None:
        """Test that listing a file (not directory) fails."""
        tool = ListFilesTool(temp_workspace)
        result = await tool.execute(path="file1.txt")

        assert isinstance(result, ToolError)
        assert result.error_type == "validation"
        assert "not a directory" in result.error_message


class TestReadFileTool:
    """Tests for ReadFileTool."""

    @pytest.mark.asyncio
    async def test_read_file_success(self, temp_workspace: Path) -> None:
        """Test successfully reading a file."""
        tool = ReadFileTool(temp_workspace)
        result = await tool.execute(path="file1.txt")

        assert isinstance(result, ToolResult)
        assert result.content == "File 1 content"
        assert result.metadata["file_size"] > 0
        assert result.metadata["line_count"] == 1

    @pytest.mark.asyncio
    async def test_read_multiline_file(self, temp_workspace: Path) -> None:
        """Test reading a file with multiple lines."""
        tool = ReadFileTool(temp_workspace)
        result = await tool.execute(path="file2.md")

        assert isinstance(result, ToolResult)
        assert "# File 2" in result.content
        assert "Markdown content" in result.content
        assert result.metadata["line_count"] == 2

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, temp_workspace: Path) -> None:
        """Test reading a nonexistent file."""
        tool = ReadFileTool(temp_workspace)
        result = await tool.execute(path="nonexistent.txt")

        assert isinstance(result, ToolError)
        assert result.error_type == "not_found"
        assert "not found" in result.error_message

    @pytest.mark.asyncio
    async def test_read_file_path_traversal_rejected(self, temp_workspace: Path) -> None:
        """Test that path traversal is rejected."""
        tool = ReadFileTool(temp_workspace)
        result = await tool.execute(path="../../../etc/passwd")

        assert isinstance(result, ToolError)
        assert result.error_type == "validation"

    @pytest.mark.asyncio
    async def test_read_file_too_large(self, temp_workspace: Path) -> None:
        """Test that files larger than MAX_FILE_SIZE are rejected."""
        large_file = temp_workspace / "large.txt"
        # Write a file larger than MAX_FILE_SIZE
        large_file.write_text("x" * (ReadFileTool.MAX_FILE_SIZE + 1))

        tool = ReadFileTool(temp_workspace)
        result = await tool.execute(path="large.txt")

        assert isinstance(result, ToolError)
        assert result.error_type == "execution"
        assert "too large" in result.error_message

    @pytest.mark.asyncio
    async def test_read_binary_file_rejected(self, temp_workspace: Path) -> None:
        """Test that binary files are rejected."""
        binary_file = temp_workspace / "binary.bin"
        # Write a file with null bytes to trigger binary detection
        binary_file.write_bytes(b"\x00\x01\x02\x03\x04")

        tool = ReadFileTool(temp_workspace)
        result = await tool.execute(path="binary.bin")

        assert isinstance(result, ToolError)
        assert result.error_type == "validation"
        assert "binary" in result.error_message

    @pytest.mark.asyncio
    async def test_read_directory_fails(self, temp_workspace: Path) -> None:
        """Test that reading a directory fails."""
        tool = ReadFileTool(temp_workspace)
        result = await tool.execute(path="subdir")

        assert isinstance(result, ToolError)
        assert result.error_type == "validation"
        assert "not a file" in result.error_message

    @pytest.mark.asyncio
    async def test_read_file_missing_path(self, temp_workspace: Path) -> None:
        """Test that missing path parameter is rejected."""
        tool = ReadFileTool(temp_workspace)
        result = await tool.execute(path=None)

        assert isinstance(result, ToolError)
        assert result.error_type == "validation"
        assert "required" in result.error_message


class TestWriteFileTool:
    """Tests for WriteFileTool."""

    @pytest.mark.asyncio
    async def test_write_file_success(self, temp_workspace: Path) -> None:
        """Test successfully writing a file."""
        tool = WriteFileTool(temp_workspace)
        new_content = "New file content"
        result = await tool.execute(path="newfile.txt", content=new_content)

        assert isinstance(result, ToolResult)
        assert "successfully" in result.content
        assert (temp_workspace / "newfile.txt").read_text() == new_content

    @pytest.mark.asyncio
    async def test_write_file_creates_parent_dirs(self, temp_workspace: Path) -> None:
        """Test that parent directories are created."""
        tool = WriteFileTool(temp_workspace)
        result = await tool.execute(
            path="new/nested/dir/file.txt",
            content="Nested file"
        )

        assert isinstance(result, ToolResult)
        assert (temp_workspace / "new" / "nested" / "dir" / "file.txt").read_text() == "Nested file"

    @pytest.mark.asyncio
    async def test_write_file_overwrites_existing(self, temp_workspace: Path) -> None:
        """Test that existing files are overwritten."""
        tool = WriteFileTool(temp_workspace)
        new_content = "Overwritten content"
        result = await tool.execute(path="file1.txt", content=new_content)

        assert isinstance(result, ToolResult)
        assert (temp_workspace / "file1.txt").read_text() == new_content

    @pytest.mark.asyncio
    async def test_write_file_path_traversal_rejected(self, temp_workspace: Path) -> None:
        """Test that path traversal is rejected."""
        tool = WriteFileTool(temp_workspace)
        result = await tool.execute(path="../outside.txt", content="content")

        assert isinstance(result, ToolError)
        assert result.error_type == "validation"

    @pytest.mark.asyncio
    async def test_write_file_missing_path(self, temp_workspace: Path) -> None:
        """Test that missing path parameter is rejected."""
        tool = WriteFileTool(temp_workspace)
        result = await tool.execute(path=None, content="content")

        assert isinstance(result, ToolError)
        assert result.error_type == "validation"
        assert "path is required" in result.error_message

    @pytest.mark.asyncio
    async def test_write_file_missing_content(self, temp_workspace: Path) -> None:
        """Test that missing content parameter is rejected."""
        tool = WriteFileTool(temp_workspace)
        result = await tool.execute(path="file.txt", content=None)

        assert isinstance(result, ToolError)
        assert result.error_type == "validation"
        assert "content is required" in result.error_message


class TestEditFileTool:
    """Tests for EditFileTool."""

    @pytest.mark.asyncio
    async def test_edit_file_success(self, temp_workspace: Path) -> None:
        """Test successfully editing a file."""
        tool = EditFileTool(temp_workspace)
        result = await tool.execute(
            path="file1.txt",
            old_content="File 1 content",
            new_content="Updated content"
        )

        assert isinstance(result, ToolResult)
        assert (temp_workspace / "file1.txt").read_text() == "Updated content"

    @pytest.mark.asyncio
    async def test_edit_file_partial_replacement(self, temp_workspace: Path) -> None:
        """Test editing a file with partial content replacement."""
        tool = EditFileTool(temp_workspace)
        result = await tool.execute(
            path="file2.md",
            old_content="File 2",
            new_content="Updated File"
        )

        assert isinstance(result, ToolResult)
        content = (temp_workspace / "file2.md").read_text()
        assert "Updated File" in content
        assert "File 2" not in content

    @pytest.mark.asyncio
    async def test_edit_file_not_found(self, temp_workspace: Path) -> None:
        """Test editing a nonexistent file."""
        tool = EditFileTool(temp_workspace)
        result = await tool.execute(
            path="nonexistent.txt",
            old_content="old",
            new_content="new"
        )

        assert isinstance(result, ToolError)
        assert result.error_type == "not_found"

    @pytest.mark.asyncio
    async def test_edit_file_content_not_found(self, temp_workspace: Path) -> None:
        """Test editing when old_content is not found."""
        tool = EditFileTool(temp_workspace)
        result = await tool.execute(
            path="file1.txt",
            old_content="nonexistent content",
            new_content="new"
        )

        assert isinstance(result, ToolError)
        assert result.error_type == "validation"
        assert "not found" in result.error_message

    @pytest.mark.asyncio
    async def test_edit_file_path_traversal_rejected(self, temp_workspace: Path) -> None:
        """Test that path traversal is rejected."""
        tool = EditFileTool(temp_workspace)
        result = await tool.execute(
            path="../outside.txt",
            old_content="old",
            new_content="new"
        )

        assert isinstance(result, ToolError)
        assert result.error_type == "validation"

    @pytest.mark.asyncio
    async def test_edit_file_directory_fails(self, temp_workspace: Path) -> None:
        """Test that editing a directory fails."""
        tool = EditFileTool(temp_workspace)
        result = await tool.execute(
            path="subdir",
            old_content="old",
            new_content="new"
        )

        assert isinstance(result, ToolError)
        assert result.error_type == "validation"
        assert "not a file" in result.error_message

    @pytest.mark.asyncio
    async def test_edit_file_missing_parameters(self, temp_workspace: Path) -> None:
        """Test that missing parameters are rejected."""
        tool = EditFileTool(temp_workspace)

        result = await tool.execute(path="file.txt", old_content=None, new_content="new")
        assert isinstance(result, ToolError)
        assert result.error_type == "validation"


class TestDeleteFileTool:
    """Tests for DeleteFileTool."""

    @pytest.mark.asyncio
    async def test_delete_file_success(self, temp_workspace: Path) -> None:
        """Test successfully deleting a file."""
        tool = DeleteFileTool(temp_workspace)
        file_path = temp_workspace / "file1.txt"
        assert file_path.exists()

        result = await tool.execute(path="file1.txt")

        assert isinstance(result, ToolResult)
        assert "successfully" in result.content
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, temp_workspace: Path) -> None:
        """Test deleting a nonexistent file."""
        tool = DeleteFileTool(temp_workspace)
        result = await tool.execute(path="nonexistent.txt")

        assert isinstance(result, ToolError)
        assert result.error_type == "not_found"

    @pytest.mark.asyncio
    async def test_delete_file_path_traversal_rejected(self, temp_workspace: Path) -> None:
        """Test that path traversal is rejected."""
        tool = DeleteFileTool(temp_workspace)
        result = await tool.execute(path="../outside.txt")

        assert isinstance(result, ToolError)
        assert result.error_type == "validation"

    @pytest.mark.asyncio
    async def test_delete_directory_fails(self, temp_workspace: Path) -> None:
        """Test that deleting a directory fails."""
        tool = DeleteFileTool(temp_workspace)
        result = await tool.execute(path="subdir")

        assert isinstance(result, ToolError)
        assert result.error_type == "validation"
        assert "not a file" in result.error_message

    @pytest.mark.asyncio
    async def test_delete_file_missing_path(self, temp_workspace: Path) -> None:
        """Test that missing path parameter is rejected."""
        tool = DeleteFileTool(temp_workspace)
        result = await tool.execute(path=None)

        assert isinstance(result, ToolError)
        assert result.error_type == "validation"
        assert "required" in result.error_message


class TestFileToolsIntegration:
    """Integration tests combining multiple file tools."""

    @pytest.mark.asyncio
    async def test_write_read_cycle(self, temp_workspace: Path) -> None:
        """Test writing a file and then reading it."""
        write_tool = WriteFileTool(temp_workspace)
        read_tool = ReadFileTool(temp_workspace)

        # Write
        content = "Test content for integration"
        write_result = await write_tool.execute(path="integration.txt", content=content)
        assert isinstance(write_result, ToolResult)

        # Read
        read_result = await read_tool.execute(path="integration.txt")
        assert isinstance(read_result, ToolResult)
        assert read_result.content == content

    @pytest.mark.asyncio
    async def test_write_edit_read_cycle(self, temp_workspace: Path) -> None:
        """Test writing, editing, and reading a file."""
        write_tool = WriteFileTool(temp_workspace)
        edit_tool = EditFileTool(temp_workspace)
        read_tool = ReadFileTool(temp_workspace)

        # Write
        original = "Original content here"
        await write_tool.execute(path="cycle.txt", content=original)

        # Edit
        edit_result = await edit_tool.execute(
            path="cycle.txt",
            old_content="Original",
            new_content="Modified"
        )
        assert isinstance(edit_result, ToolResult)

        # Read
        read_result = await read_tool.execute(path="cycle.txt")
        assert isinstance(read_result, ToolResult)
        assert "Modified content here" in read_result.content

    @pytest.mark.asyncio
    async def test_write_delete_cycle(self, temp_workspace: Path) -> None:
        """Test writing and then deleting a file."""
        write_tool = WriteFileTool(temp_workspace)
        delete_tool = DeleteFileTool(temp_workspace)

        # Write
        await write_tool.execute(path="temp.txt", content="Temporary")

        # Verify file exists
        assert (temp_workspace / "temp.txt").exists()

        # Delete
        delete_result = await delete_tool.execute(path="temp.txt")
        assert isinstance(delete_result, ToolResult)
        assert not (temp_workspace / "temp.txt").exists()

    @pytest.mark.asyncio
    async def test_nested_directory_operations(self, temp_workspace: Path) -> None:
        """Test operations in nested directories."""
        write_tool = WriteFileTool(temp_workspace)
        read_tool = ReadFileTool(temp_workspace)
        list_tool = ListFilesTool(temp_workspace)

        # Write to nested path
        nested_content = "Nested file content"
        await write_tool.execute(
            path="level1/level2/level3/deep.txt",
            content=nested_content
        )

        # Read from nested path
        read_result = await read_tool.execute(path="level1/level2/level3/deep.txt")
        assert isinstance(read_result, ToolResult)
        assert read_result.content == nested_content

        # List with appropriate depth
        list_result = await list_tool.execute(path=".", max_depth=4)
        assert isinstance(list_result, ToolResult)
        assert "deep.txt" in list_result.content
