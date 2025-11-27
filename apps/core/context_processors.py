"""Context processors for making variables available in all templates."""

import os


def build_info(request):
    """Add build version information to template context."""
    build_version = os.environ.get("BUILD_VERSION", "dev")
    vcs_ref = os.environ.get("VCS_REF", "")

    # Extract branch and SHA from BUILD_VERSION if available
    # BUILD_VERSION format: "branch-sha" (e.g., "develop-abc1234")
    build_branch = "unknown"
    build_sha = "unknown"

    if "-" in build_version and len(build_version.split("-", 1)) == 2:
        build_branch, build_sha = build_version.split("-", 1)
    elif vcs_ref:
        # Fallback to VCS_REF if available
        build_sha = vcs_ref

    return {
        "BUILD_VERSION": build_version,
        "BUILD_SHA": build_sha,
        "BUILD_BRANCH": build_branch,
    }
