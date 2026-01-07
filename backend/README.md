# Helm UI Backend - Configuration Guide

This backend provides a dynamic, configuration-driven API for generating UI forms from YAML files.

## Overview

The backend automatically generates JSON Schema from your `values.yaml` file and applies metadata from `config.yaml` to control how the UI behaves. This means you can adapt the UI to any Helm chart or YAML configuration without changing any code.

## Architecture

```
values.yaml  ──┐
               ├──> Backend (main.py) ──> JSON Schema ──> Frontend UI
config.yaml ──┘
```

## Configuration File (`config.yaml`)

The `config.yaml` file controls all UI behavior without requiring code changes.

### Structure

```yaml
# Fields that should be read-only
readonly_fields:
  - image.repository
  - image.pullPolicy
  - ingress.host

# Fields that should use their array values as enum options
enum_fields:
  - environments
  - branches

# Field descriptions (shown as help text)
field_descriptions:
  image.tag: "Docker image tag to deploy"
  service.port: "Port number for the service"

# UI sections for organizing fields
sections:
  - key: image
    title: "Docker Image Configuration"
    description: "Configure Docker image settings"
    icon: "image"

# Overall UI configuration
ui_config:
  title: "ArgoCD Deployment Manager"
  description: "Configure your deployment settings"
  confirm_before_save: true
  show_json_toggle: true
```

### Configuration Options

#### 1. Read-Only Fields

Prevent users from editing certain fields:

```yaml
readonly_fields:
  - image.repository      # Top-level field
  - image.pullPolicy      # Nested field (use dot notation)
  - ingress.host
```

**Effect**: Fields appear disabled with dashed borders and cannot be modified.

#### 2. Enum Fields

Convert array values into dropdown/checkbox options:

```yaml
enum_fields:
  - environments
  - branches
```

**Effect**: The array values from `values.yaml` become selectable options in the UI.

**Example** from `values.yaml`:
```yaml
environments: [prod, staging, test]
```
Becomes a multi-select field with those 3 options.

#### 3. Field Descriptions

Add helpful descriptions that appear below each field:

```yaml
field_descriptions:
  image.tag: "Docker image tag to deploy. Update this to deploy a different version."
  service.port: "Port number for the Kubernetes service."
  service.type: "Kubernetes service type (ClusterIP, NodePort, LoadBalancer)."
```

**Effect**: Text appears under the field as helper text.

#### 4. Sections

Organize fields into collapsible sections:

```yaml
sections:
  - key: image                              # Must match a key in values.yaml
    title: "Docker Image Configuration"     # Display title
    description: "Configure Docker images"  # Section description
    icon: "image"                           # Icon name (image, cloud, public, settings)
```

**Available Icons**:
- `image` - Docker/Image icon
- `cloud` - Cloud/Service icon
- `public` - Globe/Public icon
- `settings` - Settings/Gear icon

**Effect**: Fields are grouped into accordion sections with icons.

#### 5. UI Configuration

Control overall UI behavior:

```yaml
ui_config:
  title: "ArgoCD Deployment Manager"                    # App bar title
  description: "Configure your deployment settings"     # Page description
  confirm_before_save: true                             # Show confirmation dialog
  show_json_toggle: true                                # Show JSON preview toggle
```

## Field Path Notation

Use dot notation to reference nested fields:

```yaml
# values.yaml structure:
image:
  repository: nginx
  tag: latest
  pullPolicy: IfNotPresent

# config.yaml reference:
readonly_fields:
  - image.repository     # Refers to the 'repository' field inside 'image'
  - image.pullPolicy     # Refers to the 'pullPolicy' field inside 'image'
```

### Arrays of Objects

For arrays containing objects, use dot notation **without** array indices:

```yaml
# values.yaml structure:
ingress:
  hosts:
    - host: example.com
      tls:
        secretName: example-tls
    - host: foo.com
      tls:
        secretName: foo-tls

# config.yaml reference (NO array indices!):
field_descriptions:
  ingress.hosts: "List of ingress hosts"
  ingress.hosts.host: "Hostname for ingress rule"
  ingress.hosts.tls: "TLS configuration"
  ingress.hosts.tls.secretName: "TLS secret name"

readonly_fields:
  - ingress.hosts.tls.secretName  # Makes ALL items' secretName read-only
```

**Important**: The backend automatically detects array structures and applies configurations to all array items. You don't need `[0]`, `[1]`, etc. in your paths.

## API Endpoints

### `GET /schema`
Returns JSON Schema with all configuration applied.

**Response**:
```json
{
  "type": "object",
  "properties": { ... },
  "sections": [ ... ],
  "ui_metadata": { ... }
}
```

### `GET /values`
Returns current values from `values.yaml`.

### `POST /update`
Updates `values.yaml` with new values (respects read-only fields).

**Request Body**:
```json
{
  "image": {
    "tag": "1.20.0"
  },
  "service": {
    "port": 8080
  }
}
```

### `GET /config`
Returns the current `config.yaml` configuration.

### `POST /reload-config`
Reloads `config.yaml` without restarting the server.

## Usage Examples

### Example 1: Simple Configuration

**values.yaml**:
```yaml
appName: my-app
version: 1.0.0
replicas: 3
```

**config.yaml**:
```yaml
readonly_fields:
  - appName

field_descriptions:
  appName: "Application name (cannot be changed)"
  version: "Application version"
  replicas: "Number of pod replicas"

ui_config:
  title: "App Configuration"
  description: "Configure your application"
```

### Example 2: Complex Multi-Section Configuration

**values.yaml**:
```yaml
environments: [dev, staging, prod]

database:
  host: db.example.com
  port: 5432
  name: mydb

cache:
  enabled: true
  ttl: 3600
```

**config.yaml**:
```yaml
enum_fields:
  - environments

readonly_fields:
  - database.host

sections:
  - key: database
    title: "Database Configuration"
    description: "Configure database connection"
    icon: "cloud"

  - key: cache
    title: "Cache Configuration"
    description: "Configure caching settings"
    icon: "settings"

field_descriptions:
  database.host: "Database hostname (read-only)"
  database.port: "Database port number"
  cache.ttl: "Cache time-to-live in seconds"
```

## Adapting to Different Projects

To use this backend with a different Helm chart or YAML configuration:

1. **Replace `values.yaml`** with your Helm chart values or configuration file
2. **Update `config.yaml`** to specify:
   - Which fields should be read-only
   - Which fields should be enums
   - Field descriptions
   - How to organize fields into sections
3. **Restart the backend** - it will automatically generate the UI

No code changes required!

## Development

### Running the Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Server runs on `http://127.0.0.1:8000`

### Testing Configuration Changes

You can reload configuration without restarting:

```bash
curl -X POST http://127.0.0.1:8000/reload-config
```

Or use the frontend's refresh button after changing `config.yaml`.

## Best Practices

1. **Field Descriptions**: Always add descriptions for non-obvious fields
2. **Read-Only Fields**: Mark infrastructure fields (hosts, repositories) as read-only
3. **Sections**: Group related fields together (database, cache, service, etc.)
4. **Enum Fields**: Use for fields with a fixed set of valid values
5. **Icons**: Choose icons that match the section purpose

## Troubleshooting

### Fields Not Appearing

- Check that field names in `config.yaml` match `values.yaml` exactly
- Use dot notation for nested fields: `parent.child`

### Read-Only Not Working

- Verify the field path is correct
- Check server logs for warnings

### Configuration Not Loading

- Ensure `config.yaml` is valid YAML (use a YAML validator)
- Check server logs for errors
- Try the `/reload-config` endpoint

## Security Considerations

- Read-only fields cannot be modified via the API (enforced server-side)
- Enum fields prevent users from modifying the list of available options
- All updates are validated against the schema before being written to YAML

## Future Enhancements

Planned features:
- Field validation rules (min/max, regex patterns)
- Conditional fields (show field X only if Y is enabled)
- Custom widgets (color pickers, date pickers)
- Field groups within sections
- Multi-language support for descriptions
