"""
Database schemas for DocVault.

This package contains Pydantic models for all database entities.
"""

from .acl import DocumentACL, DocumentACLBase, DocumentACLCreate, DocumentACLUpdate
from .agent import Agent, AgentBase, AgentCreate, AgentUpdate
from .document import Document, DocumentBase, DocumentCreate, DocumentUpdate
from .organization import (
    Organization,
    OrganizationBase,
    OrganizationCreate,
    OrganizationUpdate,
)
from .permission import PermissionGrant
from .version import (
    DocumentVersion,
    DocumentVersionBase,
    DocumentVersionCreate,
    DocumentVersionUpdate,
)

# Response models (v2.2)
from .responses import (
    DocumentDetails,
    DocumentListResponse,
    OwnershipTransferResponse,
    PaginationMeta,
    PermissionListResponse,
    SearchResponse,
)

__all__ = [
    # Organization schemas
    "Organization",
    "OrganizationBase",
    "OrganizationCreate",
    "OrganizationUpdate",
    # Agent schemas
    "Agent",
    "AgentBase",
    "AgentCreate",
    "AgentUpdate",
    # Document schemas
    "Document",
    "DocumentBase",
    "DocumentCreate",
    "DocumentUpdate",
    # DocumentVersion schemas
    "DocumentVersion",
    "DocumentVersionBase",
    "DocumentVersionCreate",
    "DocumentVersionUpdate",
    # DocumentACL schemas
    "DocumentACL",
    "DocumentACLBase",
    "DocumentACLCreate",
    "DocumentACLUpdate",
    # Permission grant schema (v2.1)
    "PermissionGrant",
    # Response models (v2.2)
    "PaginationMeta",
    "DocumentListResponse",
    "SearchResponse",
    "DocumentDetails",
    "PermissionListResponse",
    "OwnershipTransferResponse",
]
