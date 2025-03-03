import json
from unittest.mock import MagicMock, patch

import pytest

from nearai.cli import RegistryCli
from nearai.cli_helpers import increment_version
from nearai.openapi_client import EntryLocation


# Fixtures for common test setup
@pytest.fixture
def mock_registry():
    """Mock the registry module."""
    with patch("nearai.cli.registry") as mock_reg:
        yield mock_reg


@pytest.fixture
def mock_config():
    """Mock the CONFIG with auth data."""
    with patch("nearai.cli.CONFIG") as mock_conf:
        mock_conf.auth = MagicMock()
        mock_conf.auth.namespace = "test-namespace"
        yield mock_conf


@pytest.fixture
def temp_agent_dir(tmp_path):
    """Create a temporary agent directory with metadata.json."""
    agent_dir = tmp_path / "test-namespace" / "test-agent" / "0.0.1"
    agent_dir.mkdir(parents=True)

    # Create metadata.json
    metadata = {"name": "test-agent", "version": "0.0.1", "description": "Test agent", "category": "agent"}

    metadata_path = agent_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f)

    # Create agent.py
    agent_path = agent_dir / "agent.py"
    with open(agent_path, "w") as f:
        f.write("# Test agent")

    return agent_dir


class TestRegistryCliUpload:
    """Tests for the RegistryCli.upload method."""

    def test_successful_upload(self, mock_registry, mock_config, tmp_path):
        """Test successful upload when version doesn't exist."""
        # Mock the helper functions
        with (
            patch("nearai.cli.load_and_validate_metadata") as mock_load_metadata,
            patch("nearai.cli.check_version_exists") as mock_check_version,
        ):
            # Setup mocks
            mock_load_metadata.return_value = ({"name": "test-agent", "version": "0.0.1"}, None)
            mock_check_version.return_value = (False, None)
            mock_registry.upload.return_value = EntryLocation(namespace="user", name="test-agent", version="0.0.1")

            # Call the method
            cli = RegistryCli()
            result = cli.upload(str(tmp_path))

            # Assertions
            assert result is not None
            assert result.namespace == "user"
            assert result.name == "test-agent"
            assert result.version == "0.0.1"
            mock_registry.upload.assert_called_once()

    def test_version_already_exists(self, mock_registry, mock_config, tmp_path, capsys):
        """Test upload failure when version already exists."""
        # Mock the helper functions
        with (
            patch("nearai.cli.load_and_validate_metadata") as mock_load_metadata,
            patch("nearai.cli.check_version_exists") as mock_check_version,
        ):
            # Setup mocks
            mock_load_metadata.return_value = ({"name": "test-agent", "version": "0.0.1"}, None)
            mock_check_version.return_value = (True, None)

            # Call the method
            cli = RegistryCli()
            result = cli.upload(str(tmp_path))

            # Assertions
            assert result is None
            captured = capsys.readouterr()
            assert "Error: Version 0.0.1 already exists" in captured.out
            assert "To upload a new version" in captured.out
            mock_registry.upload.assert_not_called()

    def test_metadata_file_not_found(self, mock_registry, mock_config, tmp_path, capsys):
        """Test upload failure when metadata.json is missing."""
        # Mock the helper function
        with patch("nearai.cli.load_and_validate_metadata") as mock_load_metadata:
            # Setup mock
            mock_load_metadata.return_value = (None, "Error: metadata.json not found")

            # Call the method
            cli = RegistryCli()
            result = cli.upload(str(tmp_path))

            # Assertions
            assert result is None
            captured = capsys.readouterr()
            assert "Error: metadata.json not found" in captured.out
            mock_registry.upload.assert_not_called()

    def test_invalid_json_metadata(self, mock_registry, mock_config, tmp_path, capsys):
        """Test upload failure when metadata.json is not valid JSON."""
        # Mock the helper function
        with patch("nearai.cli.load_and_validate_metadata") as mock_load_metadata:
            # Setup mock
            mock_load_metadata.return_value = (None, "Error: metadata.json is not a valid JSON file")

            # Call the method
            cli = RegistryCli()
            result = cli.upload(str(tmp_path))

            # Assertions
            assert result is None
            captured = capsys.readouterr()
            assert "Error: metadata.json is not a valid JSON file" in captured.out
            mock_registry.upload.assert_not_called()

    def test_missing_required_fields(self, mock_registry, mock_config, tmp_path, capsys):
        """Test upload failure when required fields are missing in metadata.json."""
        # Mock the helper function
        with patch("nearai.cli.load_and_validate_metadata") as mock_load_metadata:
            # Setup mock
            mock_load_metadata.return_value = (None, "Error: metadata.json must contain 'name' and 'version' fields")

            # Call the method
            cli = RegistryCli()
            result = cli.upload(str(tmp_path))

            # Assertions
            assert result is None
            captured = capsys.readouterr()
            assert "Error: metadata.json must contain 'name' and 'version' fields" in captured.out
            mock_registry.upload.assert_not_called()

    def test_not_logged_in(self, mock_registry, mock_config, tmp_path, capsys):
        """Test upload failure when user is not logged in."""
        # Mock the helper function
        with patch("nearai.cli.load_and_validate_metadata") as mock_load_metadata:
            # Setup mock
            mock_load_metadata.return_value = (None, "Please login with `nearai login` before uploading")

            # Call the method
            cli = RegistryCli()
            result = cli.upload(str(tmp_path))

            # Assertions
            assert result is None
            captured = capsys.readouterr()
            assert "Please login with `nearai login` before uploading" in captured.out
            mock_registry.upload.assert_not_called()

    def test_other_registry_error(self, mock_registry, mock_config, tmp_path, capsys):
        """Test upload failure when an unexpected error occurs during registry info check."""
        # Mock the helper functions
        with (
            patch("nearai.cli.load_and_validate_metadata") as mock_load_metadata,
            patch("nearai.cli.check_version_exists") as mock_check_version,
        ):
            # Setup mocks
            mock_load_metadata.return_value = ({"name": "test-agent", "version": "0.0.1"}, None)
            mock_check_version.return_value = (False, "Error checking registry: Connection failed")

            # Call the method
            cli = RegistryCli()
            result = cli.upload(str(tmp_path))

            # Assertions
            assert result is None
            captured = capsys.readouterr()
            assert "Error checking registry: Connection failed" in captured.out
            mock_registry.upload.assert_not_called()

    def test_auto_increment_version(self, mock_registry, mock_config, tmp_path, capsys):
        """Test auto-increment feature when version already exists."""
        # Create a real metadata.json for this test
        metadata = {"name": "test-agent", "version": "0.0.1"}
        metadata_path = tmp_path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Mock the helper functions
        with (
            patch("nearai.cli.load_and_validate_metadata") as mock_load_metadata,
            patch("nearai.cli.check_version_exists") as mock_check_version,
            patch("nearai.cli.increment_version", wraps=increment_version) as mock_increment,
        ):
            # Setup mocks for first check (version exists) and second check (new version doesn't exist)
            mock_load_metadata.return_value = (metadata, None)
            mock_check_version.side_effect = [(True, None), (False, None)]
            mock_registry.upload.return_value = EntryLocation(namespace="user", name="test-agent", version="0.0.2")

            # Call the method with auto_increment=True
            cli = RegistryCli()
            result = cli.upload(str(tmp_path), auto_increment=True)

            # Assertions
            assert result is not None
            assert result.version == "0.0.2"
            mock_increment.assert_called_once_with("0.0.1")
            mock_registry.upload.assert_called_once()

            # Check that metadata.json was updated
            with open(metadata_path, "r") as f:
                updated_metadata = json.load(f)
                assert updated_metadata["version"] == "0.0.2"

            # Check console output
            captured = capsys.readouterr()
            assert "Auto-incrementing to" in captured.out
            assert "Updated" in captured.out

    def test_update_version(self, mock_registry, mock_config, tmp_path, capsys):
        """Test updating version in metadata.json."""
        # Create a metadata.json file for testing
        metadata = {"name": "test-agent", "version": "1.2.3"}
        metadata_path = tmp_path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Test patch increment (default)
        cli = RegistryCli()
        result = cli.update(str(tmp_path))

        # Assertions
        assert result is True
        captured = capsys.readouterr()
        assert "Version: 1.2.3 → 1.2.4" in captured.out

        # Verify metadata was updated
        with open(metadata_path, "r") as f:
            updated_metadata = json.load(f)
            assert updated_metadata["version"] == "1.2.4"

        # Test minor increment
        result = cli.update(str(tmp_path), increment_type="minor")

        # Assertions
        assert result is True
        captured = capsys.readouterr()
        assert "Version: 1.2.4 → 1.3.0" in captured.out

        # Verify metadata was updated
        with open(metadata_path, "r") as f:
            updated_metadata = json.load(f)
            assert updated_metadata["version"] == "1.3.0"

        # Test major increment
        result = cli.update(str(tmp_path), increment_type="major")

        # Assertions
        assert result is True
        captured = capsys.readouterr()
        assert "Version: 1.3.0 → 2.0.0" in captured.out

        # Verify metadata was updated
        with open(metadata_path, "r") as f:
            updated_metadata = json.load(f)
            assert updated_metadata["version"] == "2.0.0"
