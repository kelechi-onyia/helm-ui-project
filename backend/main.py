import enum
from fastapi import FastAPI, HTTPException
import yaml
import json
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import os
import re
from git_helper import GitHelper

logging.basicConfig(level=logging.INFO)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VALUES_FILE = "../values.yaml"
CONFIG_FILE = "config.yaml"


class UpdateRequest(BaseModel):
    data: Dict[str, Any]


def load_config():
    """Load configuration from config.yaml."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as file:
                return yaml.safe_load(file) or {}
        else:
            logging.warning(f"Config file {CONFIG_FILE} not found. Using defaults.")
            return {
                "readonly_fields": [],
                "enum_fields": [],
                "field_descriptions": {},
                "sections": [],
                "ui_config": {}
            }
    except Exception as e:
        logging.error(f"Error loading config: {str(e)}")
        return {
            "readonly_fields": [],
            "enum_fields": [],
            "field_descriptions": {},
            "sections": [],
            "ui_config": {}
        }


# Load configuration at startup
config = load_config()
readonly_fields = config.get("readonly_fields", [])
enum_fields = config.get("enum_fields", [])
field_titles = config.get("field_titles", {})
field_descriptions = config.get("field_descriptions", {})
sections_config = config.get("sections", [])
ui_config = config.get("ui_config", {})

# Initialize Git helper
git_config = config.get("git_config", {})
git_helper = GitHelper(git_config)

# Initialize Git repository if enabled
if git_helper.is_enabled():
    logging.info("Git integration is enabled. Initializing repository...")
    if git_helper.init_repository():
        logging.info("Git repository initialized successfully")
        # Update VALUES_FILE to point to Git repo
        git_values_path = git_helper.get_values_file_path()
        if git_values_path:
            # Convert to absolute path
            VALUES_FILE = os.path.abspath(git_values_path)
            logging.info(f"Using values.yaml from Git repository: {VALUES_FILE}")
        else:
            logging.error("Failed to get values file path from Git repository")
    else:
        logging.error("Failed to initialize Git repository")


def get_values_file() -> str:
    """Get the path to the values.yaml file (Git or local)."""
    if git_helper.is_enabled() and git_helper.get_values_file_path():
        return git_helper.get_values_file_path()
    return "../values.yaml"


def normalize_path(path):
    """Remove array indices like [0] from field paths for config lookup."""
    return re.sub(r'\[\d+\]', '', path)


def create_json_schema(yaml_data):
    """Create JSON Schema from YAML data with configuration-based metadata."""
    schema = {
        "type": "object",
        "properties": {},
        "required": []
    }

    # Add UI configuration metadata
    if ui_config:
        schema["ui_metadata"] = ui_config

    # Add sections configuration
    if sections_config:
        schema["sections"] = sections_config

    def is_readonly(path):
        normalized = normalize_path(path)
        return normalized in readonly_fields

    def is_enum(path):
        normalized = normalize_path(path)
        return normalized in enum_fields

    def get_description(path):
        normalized = normalize_path(path)
        return field_descriptions.get(normalized, None)

    def get_title(path):
        """Get title for a field - from config or auto-generated."""
        normalized = normalize_path(path)
        # Check if custom title is defined in config
        if normalized in field_titles:
            return field_titles[normalized]
        # Otherwise auto-generate
        return get_title_from_path(path)

    def get_type_schema(value):
        """Determine JSON Schema type for a primitive value."""
        if isinstance(value, bool):
            return {"type": "boolean"}
        elif isinstance(value, int):
            return {"type": "integer"}
        elif isinstance(value, float):
            return {"type": "number"}
        else:
            return {"type": "string"}

    def get_title_from_path(path):
        """Generate a human-readable title from field path."""
        # Get the last part of the path
        parts = path.split('.')
        last_part = parts[-1]
        # Convert camelCase or snake_case to Title Case
        # Remove array indices
        clean_part = re.sub(r'\[\d+\]', '', last_part)
        # Add spaces before capitals and capitalize
        spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', clean_part)
        # Replace underscores with spaces
        spaced = spaced.replace('_', ' ')
        # Title case
        return spaced.title()

    def process_value(value, field_path):
        """Process any value and return its schema."""
        if isinstance(value, dict):
            # Nested object
            props = process_object(value, field_path)
            schema_def = {
                "type": "object",
                "properties": props,
                "title": get_title(field_path)
            }
            return schema_def

        elif isinstance(value, list):
            # Array
            if not value:
                return {
                    "type": "array",
                    "items": {"type": "string"},
                    "title": get_title(field_path)
                }

            # Check if it's an enum field (list of primitives used as options)
            if is_enum(field_path) and value and not isinstance(value[0], dict):
                return {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True,
                    "default": value,
                    "enum_values": value,
                    "title": get_title(field_path)
                }

            # Regular array - infer schema from first item
            sample_item = value[0]
            if isinstance(sample_item, dict):
                # Array of objects - process the structure
                item_schema = process_value(sample_item, f"{field_path}[0]")
                # Override the item title with custom one from config
                item_title = get_title(f"{field_path}[0]")
                # If no custom title, try to make it singular
                if item_title == get_title_from_path(f"{field_path}[0]"):
                    auto_title = get_title(field_path).rstrip('s')  # Remove plural 's'
                    if auto_title == get_title(field_path):
                        auto_title = f"{auto_title} Item"
                    item_title = auto_title
                item_schema["title"] = item_title

                return {
                    "type": "array",
                    "items": item_schema,
                    "title": get_title(field_path)
                }
            else:
                # Array of primitives
                item_type = get_type_schema(sample_item)
                return {
                    "type": "array",
                    "items": item_type,
                    "title": get_title(field_path)
                }
        else:
            # Primitive value
            schema_def = get_type_schema(value)
            schema_def["title"] = get_title(field_path)
            return schema_def

    def process_object(obj, current_path=""):
        """Process an object and return properties dict."""
        properties = {}

        for key, value in obj.items():
            field_path = f"{current_path}.{key}" if current_path else key

            # Get the schema for this value
            prop_schema = process_value(value, field_path)

            # Add read-only flag if configured
            if is_readonly(field_path):
                prop_schema["readOnly"] = True

            # Add description if configured
            description = get_description(field_path)
            if description:
                prop_schema["description"] = description

            properties[key] = prop_schema

        return properties

    # Process the root object
    schema["properties"] = process_object(yaml_data)
    return schema


@app.get("/schema")
def get_schema():
    """Load values.yaml and convert it to JSON Schema format."""
    try:
        # Pull latest changes from Git if enabled
        if git_helper.is_enabled():
            pull_result = git_helper.pull()
            if pull_result.get("success"):
                logging.info(f"Pulled latest changes: {pull_result.get('message')}")
            else:
                logging.warning(f"Git pull warning: {pull_result.get('message')}")

        with open(VALUES_FILE, "r") as file:
            values = yaml.safe_load(file) or {}

        # Create a proper JSON Schema
        schema = create_json_schema(values)

        return schema
    except Exception as e:
        logging.error(f"Error loading schema: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config")
def get_config():
    """Return the current configuration."""
    try:
        return config
    except Exception as e:
        logging.error(f"Error loading config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/update")
def update_values(data: Dict[str, Any]):
    """Update values.yaml with data from the form, only changing modified fields."""
    try:
        # Load current values
        with open(VALUES_FILE, "r") as file:
            current_values = yaml.safe_load(file) or {}

        # Helper function to check if a field should be protected
        def is_protected_field(field_path):
            """Check if a field is read-only or an enum field."""
            return field_path in readonly_fields

        # Helper function to update nested dictionaries
        def update_nested_dict(current, updates, current_path=""):
            for key, value in updates.items():
                field_path = f"{current_path}.{key}" if current_path else key

                # Skip read-only fields
                if is_protected_field(field_path):
                    logging.info(f"Skipping protected field: {field_path}")
                    continue

                # If both current and updates have a dictionary at this key
                if key in current and isinstance(current[key], dict) and isinstance(value, dict):
                    update_nested_dict(current[key], value, field_path)
                # Skip enum fields if they're in the list (preserve the enum list itself)
                elif key in enum_fields and isinstance(current.get(key), list):
                    # Keep the original list, don't update
                    logging.info(f"Skipping enum field: {key}")
                    pass
                else:
                    # For all other cases, update the value
                    current[key] = value

        # Apply updates selectively
        update_nested_dict(current_values, data)

        # Save the updated values to YAML
        with open(VALUES_FILE, "w") as file:
            yaml.dump(current_values, file, default_flow_style=False, sort_keys=False)

        # Commit and push to Git if enabled
        git_result = None
        if git_helper.is_enabled():
            git_result = git_helper.commit_and_push()
            if git_result.get("success"):
                logging.info(f"Git: {git_result.get('message')}")
            else:
                logging.warning(f"Git operation failed: {git_result.get('message')}")

        response = {"message": "Updated successfully"}
        if git_result:
            response["git"] = git_result

        return response
    except Exception as e:
        logging.error(f"Error updating values: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/values")
def get_values():
    """Return the current values from the YAML file."""
    try:
        with open(VALUES_FILE, "r") as file:
            values = yaml.safe_load(file) or {}
        return values
    except Exception as e:
        logging.error(f"Error loading values: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reload-config")
def reload_config():
    """Reload configuration from config.yaml."""
    try:
        global config, readonly_fields, enum_fields, field_titles, field_descriptions, sections_config, ui_config

        config = load_config()
        readonly_fields = config.get("readonly_fields", [])
        enum_fields = config.get("enum_fields", [])
        field_titles = config.get("field_titles", {})
        field_descriptions = config.get("field_descriptions", {})
        sections_config = config.get("sections", [])
        ui_config = config.get("ui_config", {})

        return {"message": "Configuration reloaded successfully", "config": config}
    except Exception as e:
        logging.error(f"Error reloading config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Git Operations Endpoints
@app.get("/git/status")
def get_git_status():
    """Get Git repository status."""
    try:
        status = git_helper.get_status()
        return status
    except Exception as e:
        logging.error(f"Error getting Git status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/git/pull")
def git_pull():
    """Pull latest changes from Git repository."""
    try:
        if not git_helper.is_enabled():
            raise HTTPException(status_code=400, detail="Git integration is not enabled")

        result = git_helper.pull()
        return result
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error during Git pull: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/git/push")
def git_push(message: Optional[str] = None):
    """Commit and push changes to Git repository."""
    try:
        if not git_helper.is_enabled():
            raise HTTPException(status_code=400, detail="Git integration is not enabled")

        result = git_helper.commit_and_push(message)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error during Git push: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)