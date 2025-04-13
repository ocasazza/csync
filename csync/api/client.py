# -*- coding: utf-8 -*-

"""
Confluence API client for csync.

This module provides a wrapper around the atlassian-python-api library
for interacting with Confluence.
"""

import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

from atlassian import Confluence
from atlassian.errors import ApiError

logger = logging.getLogger(__name__)


class ConfluenceClient:
    """Client for interacting with Confluence API."""

    def __init__(
        self,
        url: str,
        username: Optional[str] = None,
        token: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 180
    ):
        """
        Initialize the Confluence client.
        
        Args:
            url: The URL of the Confluence instance.
            username: The username for authentication.
            token: The API token for authentication (preferred over password).
            password: The password for authentication (not recommended).
            timeout: The timeout for API requests in seconds.
        """
        self.url = url
        self.username = username
        
        # Validate URL
        if not url:
            raise ValueError("Confluence URL is required")
        
        # Validate authentication
        if token:
            # Token-based authentication (preferred)
            self.client = Confluence(
                url=url,
                username=username,
                token=token,
                timeout=timeout
            )
        elif password:
            # Password-based authentication (fallback)
            self.client = Confluence(
                url=url,
                username=username,
                password=password,
                timeout=timeout
            )
        else:
            raise ValueError(
                "Either token or password must be provided for authentication"
            )
        
        # Test connection
        try:
            self.client.get_current_user()
            logger.info(f"Successfully connected to Confluence at {url}")
        except ApiError as e:
            logger.error(f"Failed to connect to Confluence: {e}")
            raise

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """
        Get a page by ID.
        
        Args:
            page_id: The ID of the page to get.
            
        Returns:
            The page data.
        """
        return self.client.get_page_by_id(page_id)
    
    def get_page_by_title(
        self, space_key: str, title: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a page by title.
        
        Args:
            space_key: The key of the space containing the page.
            title: The title of the page to get.
            
        Returns:
            The page data or None if not found.
        """
        return self.client.get_page_by_title(space_key, title)
    
    def get_page_content(self, page_id: str) -> str:
        """
        Get the content of a page.
        
        Args:
            page_id: The ID of the page to get content for.
            
        Returns:
            The HTML content of the page.
        """
        page = self.client.get_page_by_id(page_id, expand="body.storage")
        return page["body"]["storage"]["value"]
    
    def get_page_children(self, page_id: str) -> List[Dict[str, Any]]:
        """
        Get the children of a page.
        
        Args:
            page_id: The ID of the parent page.
            
        Returns:
            A list of child pages.
        """
        return self.client.get_page_child_by_type(page_id)
    
    def get_attachments(self, page_id: str) -> List[Dict[str, Any]]:
        """
        Get the attachments of a page.
        
        Args:
            page_id: The ID of the page.
            
        Returns:
            A list of attachments.
        """
        return self.client.get_attachments_from_content(page_id)
    
    def download_attachment(
        self, page_id: str, attachment_id: str, path: str
    ) -> None:
        """
        Download an attachment.
        
        Args:
            page_id: The ID of the page containing the attachment.
            attachment_id: The ID of the attachment to download.
            path: The path to save the attachment to.
        """
        self.client.download_attachment(attachment_id, path)
    
    def create_page(
        self,
        space: str,
        title: str,
        body: str,
        parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new page.
        
        Args:
            space: The key of the space to create the page in.
            title: The title of the page.
            body: The HTML content of the page.
            parent_id: The ID of the parent page, if any.
            
        Returns:
            The created page data.
        """
        return self.client.create_page(
            space=space,
            title=title,
            body=body,
            parent_id=parent_id,
            type="page",
            representation="storage"
        )
    
    def update_page(
        self,
        page_id: str,
        title: str,
        body: str,
        version: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update an existing page.
        
        Args:
            page_id: The ID of the page to update.
            title: The new title of the page.
            body: The new HTML content of the page.
            version: The version to update from. If None, gets the current
                version.
            
        Returns:
            The updated page data.
        """
        if version is None:
            # Get the current version
            current_page = self.get_page(page_id)
            version = current_page["version"]["number"]
        
        return self.client.update_page(
            page_id=page_id,
            title=title,
            body=body,
            type="page",
            representation="storage",
            version=version + 1
        )
    
    def upload_attachment(
        self,
        page_id: str,
        filepath: str,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload an attachment to a page.
        
        Args:
            page_id: The ID of the page to attach to.
            filepath: The path to the file to upload.
            comment: An optional comment for the attachment.
            
        Returns:
            The attachment data.
        """
        return self.client.upload_attachment(
            page_id=page_id,
            filepath=filepath,
            comment=comment or "Uploaded by csync"
        )
    
    def parse_page_url(self, url: str) -> Dict[str, str]:
        """
        Parse a Confluence page URL to extract space key and page title/ID.
        
        Args:
            url: The URL of the Confluence page.
            
        Returns:
            A dictionary containing the parsed components.
        """
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        
        result = {
            "base_url": f"{parsed.scheme}://{parsed.netloc}",
            "type": None,
            "space_key": None,
            "page_id": None,
            "title": None
        }
        
        # Handle different URL formats
        if "pages" in path_parts:
            # Format: /pages/viewpage.action?pageId=123456
            # or: /pages/123456/Page+Title
            idx = path_parts.index("pages")
            if idx + 1 < len(path_parts) and path_parts[idx + 1].isdigit():
                result["type"] = "page"
                result["page_id"] = path_parts[idx + 1]
                if idx + 2 < len(path_parts):
                    result["title"] = path_parts[idx + 2].replace("+", " ")
        elif "spaces" in path_parts:
            # Format: /spaces/SPACEKEY/pages/123456/Page+Title
            idx = path_parts.index("spaces")
            if idx + 1 < len(path_parts):
                result["type"] = "space"
                result["space_key"] = path_parts[idx + 1]
                if "pages" in path_parts[idx + 2:]:
                    page_idx = path_parts.index("pages")
                    if (page_idx + 1 < len(path_parts) and
                            path_parts[page_idx + 1].isdigit()):
                        result["type"] = "page"
                        result["page_id"] = path_parts[page_idx + 1]
                        if page_idx + 2 < len(path_parts):
                            result["title"] = path_parts[page_idx + 2].replace(
                                "+", " "
                            )
        
        # Handle query parameters for legacy URLs
        if parsed.query:
            params = dict(param.split("=") for param in parsed.query.split("&"))
            if "pageId" in params:
                result["type"] = "page"
                result["page_id"] = params["pageId"]
            if "spaceKey" in params:
                result["space_key"] = params["spaceKey"]
        
        return result
