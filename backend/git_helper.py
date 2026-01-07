"""
Git Helper Module for Helm UI
Handles Git operations: clone, pull, commit, push
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from git import Repo, GitCommandError, Actor
from git.exc import InvalidGitRepositoryError, NoSuchPathError

logger = logging.getLogger(__name__)


class GitHelper:
    """Helper class for Git operations."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Git helper with configuration.

        Args:
            config: Git configuration dictionary from config.yaml
        """
        self.enabled = config.get("enabled", False)
        self.repo_url = config.get("repo_url", "")
        self.branch = config.get("branch", "main")
        self.values_path = config.get("values_path", "values.yaml")
        self.local_path = config.get("local_path", "./git-repo")
        self.author_name = config.get("author_name", "Helm UI Bot")
        self.author_email = config.get("author_email", "helm-ui@example.com")
        self.commit_message_template = config.get(
            "commit_message_template",
            "Update values via Helm UI\n\nTimestamp: {timestamp}",
        )

        # Auth config
        auth_config = config.get("auth", {})
        self.auth_method = auth_config.get("method", "token")
        self.token = auth_config.get("token", "")
        self.ssh_key_path = auth_config.get("ssh_key_path", "")

        # Auto-sync options
        self.auto_pull_on_start = config.get("auto_pull_on_start", True)
        self.auto_push_on_update = config.get("auto_push_on_update", True)

        self.repo: Optional[Repo] = None

    def is_enabled(self) -> bool:
        """Check if Git integration is enabled."""
        return self.enabled and bool(self.repo_url)

    def get_auth_url(self) -> str:
        """Get repository URL with authentication if using token."""
        if self.auth_method == "token" and self.token:
            # Insert token into HTTPS URL
            if self.repo_url.startswith("https://"):
                # https://github.com/user/repo.git -> https://token@github.com/user/repo.git
                return self.repo_url.replace("https://", f"https://{self.token}@")
        return self.repo_url

    def get_git_env(self) -> Dict[str, str]:
        """Get environment variables for Git operations."""
        env = os.environ.copy()

        # Set SSH key if using SSH auth
        if self.auth_method == "ssh" and self.ssh_key_path:
            # Expand ~ in path
            expanded_path = os.path.expanduser(self.ssh_key_path)
            env["GIT_SSH_COMMAND"] = (
                f"ssh -i {expanded_path} -o StrictHostKeyChecking=no"
            )

        return env

    def init_repository(self) -> bool:
        """
        Initialize Git repository (clone or use existing).

        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            logger.info("Git integration is disabled")
            return False

        try:
            # Check if local path exists and is a git repo
            if os.path.exists(self.local_path):
                try:
                    self.repo = Repo(self.local_path)
                    logger.info(f"Using existing repository at {self.local_path}")

                    # Ensure we're on the correct branch
                    if self.repo.active_branch.name != self.branch:
                        logger.info(f"Switching to branch {self.branch}")
                        self.repo.git.checkout(self.branch)

                    # Pull latest changes if configured
                    if self.auto_pull_on_start:
                        self.pull()

                    return True
                except InvalidGitRepositoryError:
                    logger.warning(
                        f"{self.local_path} exists but is not a git repository. Removing..."
                    )
                    import shutil

                    shutil.rmtree(self.local_path)

            # Clone repository
            logger.info(f"Cloning repository {self.repo_url} to {self.local_path}")
            auth_url = self.get_auth_url()
            env = self.get_git_env()

            self.repo = Repo.clone_from(
                auth_url, self.local_path, branch=self.branch, env=env
            )

            logger.info("Repository cloned successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing repository: {str(e)}")
            return False

    def pull(self) -> Dict[str, Any]:
        """
        Pull latest changes from remote repository.

        Returns:
            Dictionary with status and message
        """
        if not self.repo:
            return {"success": False, "message": "Repository not initialized"}

        try:
            logger.info(f"Pulling latest changes from {self.branch}")
            env = self.get_git_env()

            origin = self.repo.remotes.origin

            # Update remote URL with auth credentials if using token
            if self.auth_method == "token" and self.token:
                auth_url = self.get_auth_url()
                origin.set_url(auth_url)

            origin.pull(self.branch, env=env)

            logger.info("Pull completed successfully")
            return {
                "success": True,
                "message": f"Successfully pulled latest changes from {self.branch}",
                "commit": str(self.repo.head.commit),
            }

        except GitCommandError as e:
            logger.error(f"Git pull error: {str(e)}")
            return {"success": False, "message": f"Git pull failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Error during pull: {str(e)}")
            return {"success": False, "message": f"Pull failed: {str(e)}"}

    def commit_and_push(self, message: Optional[str] = None) -> Dict[str, Any]:
        """
        Commit changes and push to remote repository.

        Args:
            message: Custom commit message (optional)

        Returns:
            Dictionary with status and message
        """
        if not self.repo:
            return {"success": False, "message": "Repository not initialized"}

        try:
            # Check if there are changes to commit
            if not self.repo.is_dirty(untracked_files=True):
                logger.info("No changes to commit")
                return {"success": True, "message": "No changes to commit"}

            # Stage changes - use relative path from repo root
            # GitPython expects paths relative to repo root
            self.repo.index.add([self.values_path])

            # Generate commit message
            if not message:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = self.commit_message_template.format(
                    timestamp=timestamp, user="Helm UI"
                )

            # Create Actor objects for commit author
            author = Actor(self.author_name, self.author_email)
            committer = Actor(self.author_name, self.author_email)

            # Commit
            self.repo.index.commit(message, author=author, committer=committer)
            logger.info(f"Changes committed: {message}")

            # Push
            if self.auto_push_on_update:
                try:
                    env = self.get_git_env()
                    origin = self.repo.remotes.origin

                    # Update remote URL with auth credentials if using token
                    if self.auth_method == "token" and self.token:
                        auth_url = self.get_auth_url()
                        origin.set_url(auth_url)
                        logger.info("Updated remote URL with authentication")

                    logger.info(f"Attempting to push to remote repository")
                    logger.info(f"Current branch: {self.repo.active_branch.name}")
                    logger.info(f"Using auth method: {self.auth_method}")

                    # Push the current branch to remote
                    push_info = origin.push(env=env)

                    logger.info(f"Push info: {push_info}")
                    logger.info("Changes pushed successfully")

                    return {
                        "success": True,
                        "message": f"Changes committed and pushed to {self.branch}",
                        "commit": str(self.repo.head.commit),
                    }
                except GitCommandError as git_err:
                    logger.error(f"Git push command error: {git_err}")
                    logger.error(f"Git error stdout: {git_err.stdout}")
                    logger.error(f"Git error stderr: {git_err.stderr}")
                    return {
                        "success": False,
                        "message": f"Git push failed: {git_err.stderr or str(git_err)}",
                    }
                except Exception as push_err:
                    logger.error(f"Push error: {push_err}")
                    logger.error(f"Error type: {type(push_err).__name__}")
                    import traceback

                    logger.error(f"Traceback: {traceback.format_exc()}")
                    return {
                        "success": False,
                        "message": f"Push failed: {str(push_err)}",
                    }
            else:
                return {
                    "success": True,
                    "message": "Changes committed locally (auto-push disabled)",
                    "commit": str(self.repo.head.commit),
                }

        except GitCommandError as e:
            logger.error(f"Git commit/push error: {str(e)}")
            return {"success": False, "message": f"Git operation failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Error during commit/push: {str(e)}")
            return {"success": False, "message": f"Commit/push failed: {str(e)}"}

    def get_status(self) -> Dict[str, Any]:
        """
        Get Git repository status.

        Returns:
            Dictionary with repository status information
        """
        if not self.is_enabled():
            return {"enabled": False, "message": "Git integration is disabled"}

        if not self.repo:
            return {
                "enabled": True,
                "initialized": False,
                "message": "Repository not initialized",
            }

        try:
            status = {
                "enabled": True,
                "initialized": True,
                "repo_url": self.repo_url,
                "branch": self.branch,
                "current_branch": self.repo.active_branch.name,
                "last_commit": {
                    "sha": str(self.repo.head.commit),
                    "message": self.repo.head.commit.message.strip(),
                    "author": str(self.repo.head.commit.author),
                    "date": self.repo.head.commit.committed_datetime.isoformat(),
                },
                "has_changes": self.repo.is_dirty(untracked_files=True),
                "untracked_files": self.repo.untracked_files,
                "modified_files": [item.a_path for item in self.repo.index.diff(None)],
            }

            return status

        except Exception as e:
            logger.error(f"Error getting repository status: {str(e)}")
            return {"enabled": True, "initialized": True, "error": str(e)}

    def get_values_file_path(self) -> str:
        """Get the full path to the values.yaml file in the repository."""
        if self.repo:
            return os.path.join(self.local_path, self.values_path)
        return ""

    def sync_values_file(self, source_path: str) -> bool:
        """
        Sync values file from source to Git repository.

        Args:
            source_path: Path to the source values.yaml file

        Returns:
            True if successful, False otherwise
        """
        if not self.repo:
            return False

        try:
            target_path = self.get_values_file_path()
            import shutil

            shutil.copy2(source_path, target_path)
            logger.info(f"Values file synced from {source_path} to {target_path}")
            return True
        except Exception as e:
            logger.error(f"Error syncing values file: {str(e)}")
            return False

