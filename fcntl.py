"""Minimal fcntl stub for Windows test environments.
This file exists only to allow importing Home Assistant modules that
import fcntl on POSIX systems. It should be a no-op stub used during tests.
"""

# Basic constants used by some modules (values chosen arbitrarily)
F_GETFL = 3
F_SETFL = 4


def fcntl(fd, cmd, arg=0):
    """No-op fcntl replacement for Windows tests."""
    # Return a plausible integer
    return 0


def ioctl(fd, request, arg=0):
    """No-op ioctl replacement for Windows tests."""
    return 0
