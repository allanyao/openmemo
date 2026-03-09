"""
OpenMemo Upgrade Utilities

Provides version checking and upgrade helpers for the CLI.
"""

import importlib.metadata
import json
import sys
import subprocess


REMOTE_VERSION_URL = "https://api.openmemo.ai/version"

SCHEMA_VERSION = 2


def get_local_versions():
    """Return dict with local core version, adapter version, and schema version."""
    core_version = None
    adapter_version = None

    try:
        core_version = importlib.metadata.version("openmemo")
    except importlib.metadata.PackageNotFoundError:
        pass

    try:
        adapter_version = importlib.metadata.version("openmemo-openclaw")
    except importlib.metadata.PackageNotFoundError:
        pass

    return {
        "core": core_version,
        "adapter": adapter_version,
        "schema_version": SCHEMA_VERSION,
    }


def get_remote_versions():
    """Fetch latest versions from api.openmemo.ai/version."""
    try:
        import urllib.request
        req = urllib.request.Request(REMOTE_VERSION_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        return {
            "latest_core": data.get("latest_core"),
            "latest_adapter": data.get("latest_adapter"),
            "schema_version": data.get("schema_version"),
        }
    except Exception:
        return None


def version_check():
    """Compare local vs remote versions. Returns a dict with comparison info."""
    local = get_local_versions()
    remote = get_remote_versions()

    result = {
        "local": local,
        "remote": remote,
        "update_available": False,
    }

    if remote:
        if local["core"] and remote.get("latest_core"):
            result["update_available"] = _is_newer(remote["latest_core"], local["core"])
        if local["adapter"] and remote.get("latest_adapter"):
            adapter_newer = _is_newer(remote["latest_adapter"], local["adapter"])
            result["update_available"] = result["update_available"] or adapter_newer

    return result


def _is_newer(remote_ver, local_ver):
    """Return True if remote version is newer than local version."""
    try:
        remote_parts = [int(x) for x in remote_ver.split(".")]
        local_parts = [int(x) for x in local_ver.split(".")]
        return remote_parts > local_parts
    except (ValueError, AttributeError):
        return False


def run_upgrade():
    """Execute pip install -U openmemo openmemo-openclaw."""
    cmd = [sys.executable, "-m", "pip", "install", "-U", "openmemo", "openmemo-openclaw"]
    return subprocess.run(cmd)
