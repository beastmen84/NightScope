"""Application-layer composition and orchestration boundaries."""

from astro_viewer.app.application.dependencies import (
    AppControllerDependencies,
    build_app_controller_dependencies,
)

__all__ = [
    "AppControllerDependencies",
    "build_app_controller_dependencies",
]
