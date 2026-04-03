# Copyright 2025 deep-bi
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Any

import yaml

from . import exceptions


def load_config(config_path: str) -> dict[str, Any]:
    """Load and parse YAML configuration file.

    Args:
        config_path: Path to the YAML config file

    Returns:
        Dictionary containing configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is not valid YAML
    """
    with open(config_path) as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise exceptions.ConfigValidationError("Config must be a dictionary")

    return config


def validate_config(config: dict[str, Any]) -> None:
    """Validate that config contains required fields.

    Args:
        config: Configuration dictionary

    Raises:
        ConfigValidationError: If required fields are missing
    """
    required_fields = ["host", "port", "user", "database", "repository"]

    for field in required_fields:
        if field not in config:
            raise exceptions.ConfigValidationError(f"Missing required config field: {field}")

    _validate_tls_section(config.get("tls"))
    _validate_table_inventory_section(config.get("table_inventory"))
    _validate_minio_section(config.get("minio"))


def minio_repo_name(minio: dict[str, Any]) -> str:
    """Resolve repository name from minio config (supports repo_name or repoName)."""
    name = minio.get("repo_name") or minio.get("repoName")
    if not name or not isinstance(name, str):
        raise exceptions.ConfigValidationError(
            "minio configuration requires 'repo_name' (or 'repoName') as a non-empty string"
        )
    return name


def normalize_minio_config(minio: dict[str, Any]) -> dict[str, str]:
    """Return minio settings for S3 clients (prune). Does not include secret key."""
    _validate_minio_section(minio)
    path_val = minio.get("path")
    if path_val is None:
        path_str = ""
    elif not isinstance(path_val, str):
        raise exceptions.ConfigValidationError("minio 'path' must be a string if provided")
    else:
        path_str = path_val

    return {
        "endpoint": str(minio["endpoint"]),
        "bucket": str(minio["bucket"]),
        "path": path_str,
        "access_key": str(minio["access_key"]),
        "repo_name": minio_repo_name(minio),
    }


def get_ops_database(config: dict[str, Any]) -> str:
    """Get the ops database name from config, defaulting to 'ops'."""
    return config.get("ops_database", "ops")


def get_table_inventory_entries(config: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Extract table inventory entries from config.

    Args:
        config: Configuration dictionary

    Returns:
        List of tuples (group, database, table)
    """
    table_inventory = config.get("table_inventory")
    if not table_inventory:
        return []

    entries = []
    for group_entry in table_inventory:
        group = group_entry["group"]
        for table_entry in group_entry["tables"]:
            entries.append((group, table_entry["database"], table_entry["table"]))

    return entries


def _validate_tls_section(tls_config) -> None:
    if tls_config is None:
        return

    if not isinstance(tls_config, dict):
        raise exceptions.ConfigValidationError("TLS configuration must be a dictionary")

    enabled = bool(tls_config.get("enabled", False))

    if enabled and not tls_config.get("ca_cert"):
        raise exceptions.ConfigValidationError(
            "TLS configuration requires 'ca_cert' when 'enabled' is true"
        )

    if "verify_server_cert" in tls_config and not isinstance(
        tls_config["verify_server_cert"], bool
    ):
        raise exceptions.ConfigValidationError(
            "TLS configuration field 'verify_server_cert' must be a boolean if provided"
        )

    if "tls_versions" in tls_config:
        tls_versions = tls_config["tls_versions"]
        if not isinstance(tls_versions, list) or not all(
            isinstance(version, str) for version in tls_versions
        ):
            raise exceptions.ConfigValidationError(
                "TLS configuration field 'tls_versions' must be a list of strings if provided"
            )


def _validate_minio_section(minio_config) -> None:
    if minio_config is None:
        return

    if not isinstance(minio_config, dict):
        raise exceptions.ConfigValidationError("'minio' configuration must be a dictionary")

    minio_repo_name(minio_config)

    for field in ("endpoint", "bucket", "access_key"):
        if field not in minio_config:
            raise exceptions.ConfigValidationError(f"minio configuration requires '{field}'")
        if not isinstance(minio_config[field], str) or not str(minio_config[field]).strip():
            raise exceptions.ConfigValidationError(f"minio '{field}' must be a non-empty string")

    if "path" in minio_config and not isinstance(minio_config["path"], str):
        raise exceptions.ConfigValidationError("minio 'path' must be a string if provided")


def _validate_table_inventory_section(table_inventory) -> None:
    if table_inventory is None:
        return

    if not isinstance(table_inventory, list):
        raise exceptions.ConfigValidationError("'table_inventory' must be a list")

    for entry in table_inventory:
        if not isinstance(entry, dict):
            raise exceptions.ConfigValidationError(
                "Each entry in 'table_inventory' must be a dictionary"
            )

        if "group" not in entry:
            raise exceptions.ConfigValidationError(
                "Each entry in 'table_inventory' must have a 'group' field"
            )

        if "tables" not in entry:
            raise exceptions.ConfigValidationError(
                "Each entry in 'table_inventory' must have a 'tables' field"
            )

        if not isinstance(entry["group"], str):
            raise exceptions.ConfigValidationError("'group' field must be a string")

        tables = entry["tables"]
        if not isinstance(tables, list):
            raise exceptions.ConfigValidationError("'tables' field must be a list")

        for table_entry in tables:
            if not isinstance(table_entry, dict):
                raise exceptions.ConfigValidationError("Each table entry must be a dictionary")

            if "database" not in table_entry or "table" not in table_entry:
                raise exceptions.ConfigValidationError(
                    "Each table entry must have 'database' and 'table' fields"
                )

            if not isinstance(table_entry["database"], str) or not isinstance(
                table_entry["table"], str
            ):
                raise exceptions.ConfigValidationError(
                    "'database' and 'table' fields must be strings"
                )
