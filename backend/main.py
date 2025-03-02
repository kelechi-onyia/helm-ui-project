import enum
from fastapi import FastAPI, HTTPException
import yaml
import json
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import logging

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

# Create a list of fields that should be read-only
readonly_fields = [
    "image.repository",  # Make the image repository read-only
    "image.pullPolicy",
    "ingress.host",
]

# fields that should be dropdown list in the UI
dropdown_fields = [
    "environments",
]


class UpdateRequest(BaseModel):
    data: Dict[str, Any]


def create_json_schema(yaml_data):
    schema = {
        "type": "object",
        "properties": {},
        "required": []
    }

    # Helper function to check if a field path should be read-only
    def is_readonly(path):
        return path in readonly_fields

    def is_dropdown(path):
        return path in dropdown_fields

    def process_object(obj, current_path=""):
        properties = {}
        readonly_props = []  # Track readonly properties

        for key, value in obj.items():
            field_path = f"{current_path}.{key}" if current_path else key

            if isinstance(value, dict):
                # Process nested objects
                nested_props, nested_readonly = process_object(
                    value, field_path)
                properties[key] = {
                    "type": "object",
                    "properties": nested_props
                }
                # Add nested readonly properties to our list
                readonly_props.extend(nested_readonly)
            else:
                # Define schema for leaf properties
                prop_schema = get_property_schema(value)
                # Mark as read-only if in the list
                if is_readonly(field_path):
                    # Changed from string to boolean
                    prop_schema["readOnly"] = True
                    readonly_props.append(field_path)
                if is_dropdown(field_path):
                    prop_schema = {
                        "enum": value,
                        # "type": "string"
                    }
                properties[key] = prop_schema

        return properties, readonly_props

    def get_property_schema(value):
        """Get schema definition based on value type."""
        if isinstance(value, bool):
            return {"type": "boolean"}
        elif isinstance(value, int):
            return {"type": "integer"}
        elif isinstance(value, float):
            return {"type": "number"}
        elif isinstance(value, list):
            if not value:
                return {"type": "array", "items": {"type": "string"}}
            sample_item = value[0]
            if isinstance(sample_item, dict):
                return {"type": "array", "items": {"type": "object"}}
            else:
                return {"type": "array", "items": {"type": get_property_schema(sample_item)["type"]}}
        else:
            return {"type": "string"}

    # Process the root object
    schema["properties"], _ = process_object(
        yaml_data)  # Properly unpack the tuple
    return schema


@app.get("/schema")
def get_schema():
    """Load values.yaml and convert it to JSON Schema format."""
    try:
        with open(VALUES_FILE, "r") as file:
            values = yaml.safe_load(file) or {}

        # Create a proper JSON Schema
        schema = create_json_schema(values)

        return schema
    except Exception as e:
        logging.error(f"Error loading schema: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/update")
def update_values(data: Dict[str, Any]):
    """Update values.yaml with data from the form, only changing modified fields."""
    try:
        # Load current values
        with open(VALUES_FILE, "r") as file:
            current_values = yaml.safe_load(file) or {}

        # Helper function to update nested dictionaries
        def update_nested_dict(current, updates):
            for key, value in updates.items():
                # If both current and updates have a dictionary at this key
                if key in current and isinstance(current[key], dict) and isinstance(value, dict):
                    update_nested_dict(current[key], value)
                # Skip dropdown fields if they're in the list of protected dropdowns
                elif key in dropdown_fields and isinstance(current.get(key), list):
                    # Keep the original list, don't update
                    pass
                else:
                    # For all other cases, update the value
                    current[key] = value

        # Apply updates selectively
        update_nested_dict(current_values, data)

        # Save the updated values to YAML
        with open(VALUES_FILE, "w") as file:
            yaml.dump(current_values, file, default_flow_style=False)

        return {"message": "Updated successfully"}
    except Exception as e:
        logging.error(f"Error updating values: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# @app.post("/update")
# def update_values(data: Dict[str, Any]):
#     """Update values.yaml with data from the form."""
#     try:
#         # Save the updated values to YAML
#         with open(VALUES_FILE, "w") as file:
#             yaml.dump(data, file, default_flow_style=False)
#
#         return {"message": "Updated successfully"}
#     except Exception as e:
#         logging.error(f"Error loading schema: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))


@app.get("/values")
def get_values():
    """Return the current values from the YAML file."""
    try:
        with open(VALUES_FILE, "r") as file:
            values = yaml.safe_load(file) or {}
        return values
    except Exception as e:
        logging.error(f"Error loading schema: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
