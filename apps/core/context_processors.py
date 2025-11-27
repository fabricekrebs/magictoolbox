"""Context processors for making variables available in all templates."""

import os


def build_info(request):
    """Add build version information to template context."""
    return {
        "BUILD_VERSION": os.environ.get("BUILD_VERSION", "dev"),
        "BUILD_SHA": os.environ.get("BUILD_SHA", "unknown"),
        "BUILD_BRANCH": os.environ.get("BUILD_BRANCH", "unknown"),
    }
