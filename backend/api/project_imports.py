"""Helper module for importing from project root's app folder.

The backend has its own 'app' folder which shadows the project root's 'app' folder.
This module uses importlib to explicitly load modules from the project root.
"""

import importlib.util
import sys
from pathlib import Path

# Project root is 2 levels up from backend/app/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

def _load_module_with_clean_app(name: str, path: Path):
    """Load a module, clearing backend's 'app' from sys.modules.

    This ensures the module can import from the project root's app folder
    rather than the backend's app folder. The project root's app modules
    remain in sys.modules after loading.
    """
    # Remove backend's app.* submodules (but keep app itself and project_imports!)
    for key in list(sys.modules.keys()):
        if key.startswith("app."):
            if key == "app.project_imports":
                continue  # Don't delete ourselves!
            # Check if this module is from the backend folder
            mod = sys.modules[key]
            if hasattr(mod, "__file__") and mod.__file__ and "backend" in mod.__file__:
                del sys.modules[key]

    # Ensure project root is first in path
    project_str = str(PROJECT_ROOT)
    if project_str not in sys.path:
        sys.path.insert(0, project_str)
    elif sys.path[0] != project_str:
        sys.path.remove(project_str)
        sys.path.insert(0, project_str)

    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Pre-load config (doesn't have complex deps)
_config_module = _load_module_with_clean_app(
    "project_config", PROJECT_ROOT / "app" / "config.py"
)

# Export commonly used items from config
config = _config_module.config
get_data_source = _config_module.get_data_source
set_data_source_override = _config_module.set_data_source_override
get_agent_mode = _config_module.get_agent_mode
DataSource = _config_module.DataSource

# Lazy loaders for modules with complex dependencies
_usage_tracker_module = None


def get_usage_tracker():
    """Get usage tracker (lazily loaded)."""
    global _usage_tracker_module
    if _usage_tracker_module is None:
        _usage_tracker_module = _load_module_with_clean_app(
            "project_usage_tracker", PROJECT_ROOT / "app" / "services" / "usage_tracker.py"
        )
    return _usage_tracker_module.get_usage_tracker()


def get_agent_modules():
    """Lazily load agent modules (they have heavy dependencies)."""
    logging_setup = _load_module_with_clean_app(
        "project_logging_setup", PROJECT_ROOT / "app" / "agents" / "logging_setup.py"
    )
    graph = _load_module_with_clean_app(
        "project_graph", PROJECT_ROOT / "app" / "agents" / "graph.py"
    )
    shared = _load_module_with_clean_app(
        "project_shared", PROJECT_ROOT / "app" / "agents" / "tools" / "shared.py"
    )
    return {
        "setup_agent_logging": logging_setup.setup_agent_logging,
        "run_pipeline": graph.run_pipeline,
        "set_shared_data": shared.set_shared_data,
    }
