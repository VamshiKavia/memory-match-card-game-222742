import json
from pathlib import Path

from src.api.main import app

"""
Script to generate OpenAPI schema for distribution to dependent containers.

Usage:
    Run from the backend directory (where this file's parent is on PYTHONPATH):
        python -m src.api.generate_openapi

This will create/update interfaces/openapi.json at the backend root.
"""


def _resolve_output_path() -> str:
    """
    Resolve the output path for interfaces/openapi.json relative to the backend root.
    Assumes this script is executed with CWD as the backend directory.
    """
    output_dir = Path("interfaces")
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir / "openapi.json")


def main() -> None:
    """Generate and write the OpenAPI schema to interfaces/openapi.json."""
    # PUBLIC_INTERFACE
    openapi_schema = app.openapi()
    output_path = _resolve_output_path()
    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"OpenAPI schema written to {output_path}")


if __name__ == "__main__":
    main()
