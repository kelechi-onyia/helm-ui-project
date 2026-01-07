"""
Environment variable configuration loader.
Allows overriding config.yaml settings with environment variables.
"""

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def str_to_bool(value: str) -> bool:
    """Convert string to boolean."""
    return value.lower() in ('true', '1', 'yes', 'on')


def load_git_config_from_env() -> Dict[str, Any]:
    """
    Load Git configuration from environment variables.
    Environment variables take precedence over config.yaml.
    """
    git_config = {}

    # Basic Git settings
    if os.getenv('GIT_ENABLED') is not None:
        git_config['enabled'] = str_to_bool(os.getenv('GIT_ENABLED'))

    if os.getenv('GIT_REPO_URL'):
        git_config['repo_url'] = os.getenv('GIT_REPO_URL')

    if os.getenv('GIT_BRANCH'):
        git_config['branch'] = os.getenv('GIT_BRANCH')

    if os.getenv('GIT_VALUES_PATH'):
        git_config['values_path'] = os.getenv('GIT_VALUES_PATH')

    if os.getenv('GIT_LOCAL_PATH'):
        git_config['local_path'] = os.getenv('GIT_LOCAL_PATH')

    if os.getenv('GIT_AUTHOR_NAME'):
        git_config['author_name'] = os.getenv('GIT_AUTHOR_NAME')

    if os.getenv('GIT_AUTHOR_EMAIL'):
        git_config['author_email'] = os.getenv('GIT_AUTHOR_EMAIL')

    # Auto-sync options
    if os.getenv('GIT_AUTO_PULL_ON_START') is not None:
        git_config['auto_pull_on_start'] = str_to_bool(os.getenv('GIT_AUTO_PULL_ON_START'))

    if os.getenv('GIT_AUTO_PUSH_ON_UPDATE') is not None:
        git_config['auto_push_on_update'] = str_to_bool(os.getenv('GIT_AUTO_PUSH_ON_UPDATE'))

    # Authentication settings
    auth_config = {}

    if os.getenv('GIT_AUTH_METHOD'):
        auth_config['method'] = os.getenv('GIT_AUTH_METHOD')

    if os.getenv('GIT_SSH_KEY_PATH'):
        auth_config['ssh_key_path'] = os.getenv('GIT_SSH_KEY_PATH')

    if os.getenv('GIT_TOKEN'):
        auth_config['token'] = os.getenv('GIT_TOKEN')

    if auth_config:
        git_config['auth'] = auth_config

    # Commit message template
    if os.getenv('GIT_COMMIT_MESSAGE_TEMPLATE'):
        git_config['commit_message_template'] = os.getenv('GIT_COMMIT_MESSAGE_TEMPLATE')

    return git_config


def merge_configs(file_config: Dict[str, Any], env_overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge file configuration with environment variable overrides.
    Environment variables take precedence.

    Args:
        file_config: Configuration loaded from config.yaml
        env_overrides: Configuration from environment variables

    Returns:
        Merged configuration dictionary
    """
    merged = file_config.copy()

    for key, value in env_overrides.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            # Merge nested dictionaries
            merged[key] = {**merged[key], **value}
        else:
            # Override with env value
            merged[key] = value

    return merged


def load_config_with_env(file_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load configuration and override with environment variables.

    Args:
        file_config: Configuration loaded from config.yaml

    Returns:
        Final configuration with environment variable overrides applied
    """
    # Load Git config from environment
    env_git_config = load_git_config_from_env()

    # Get current git_config from file
    file_git_config = file_config.get('git_config', {})

    # Merge git configurations
    final_git_config = merge_configs(file_git_config, env_git_config)

    # Update the main config
    final_config = file_config.copy()
    if final_git_config:
        final_config['git_config'] = final_git_config

    # Log which values were overridden
    if env_git_config:
        logger.info("Git configuration overridden by environment variables:")
        for key in env_git_config:
            if key != 'auth' or 'token' not in env_git_config.get('auth', {}):
                logger.info(f"  - {key}: {env_git_config[key]}")
            else:
                logger.info(f"  - auth.token: [REDACTED]")

    return final_config