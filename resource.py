"""Minimal resource stub for Windows test environments.
Provides set_open_file_descriptor_limit used by Home Assistant utilities.
"""

def set_open_file_descriptor_limit(limit: int = 1024) -> None:
    """No-op replacement for POSIX resource.setrlimit usage in tests on Windows."""
    # Intentionally do nothing on Windows
    return
