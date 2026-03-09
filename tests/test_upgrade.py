import pytest
from unittest.mock import patch, MagicMock
from openmemo.upgrade import get_local_versions, version_check, _is_newer, run_upgrade


class TestGetLocalVersions:
    def test_returns_dict(self):
        result = get_local_versions()
        assert isinstance(result, dict)
        assert "core" in result
        assert "adapter" in result
        assert "schema_version" in result

    def test_core_version_detected(self):
        result = get_local_versions()
        assert result["core"] is not None

    def test_schema_version_is_int(self):
        result = get_local_versions()
        assert isinstance(result["schema_version"], int)


class TestIsNewer:
    def test_newer(self):
        assert _is_newer("1.1.0", "1.0.0") is True

    def test_same(self):
        assert _is_newer("1.0.0", "1.0.0") is False

    def test_older(self):
        assert _is_newer("0.9.0", "1.0.0") is False

    def test_major_bump(self):
        assert _is_newer("2.0.0", "1.9.9") is True

    def test_patch_bump(self):
        assert _is_newer("1.0.1", "1.0.0") is True

    def test_invalid_version(self):
        assert _is_newer("abc", "1.0.0") is False

    def test_none_version(self):
        assert _is_newer(None, "1.0.0") is False


class TestVersionCheck:
    @patch("openmemo.upgrade.get_remote_versions")
    def test_no_remote(self, mock_remote):
        mock_remote.return_value = None
        result = version_check()
        assert result["update_available"] is False

    @patch("openmemo.upgrade.get_remote_versions")
    def test_update_available(self, mock_remote):
        mock_remote.return_value = {
            "latest_core": "99.0.0",
            "latest_adapter": "99.0.0",
            "schema_version": "2",
        }
        result = version_check()
        assert result["update_available"] is True

    @patch("openmemo.upgrade.get_remote_versions")
    def test_no_update(self, mock_remote):
        mock_remote.return_value = {
            "latest_core": "0.0.1",
            "latest_adapter": "0.0.1",
            "schema_version": "1",
        }
        result = version_check()
        assert result["update_available"] is False
