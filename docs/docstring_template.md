# DocVault Docstring Template

All public methods in the DocVault SDK must include comprehensive docstrings following this template.

## Template Structure

```python
async def method_name(
    self,
    param1: str,
    param2: Optional[int] = None,
) -> ReturnType:
    """
    Brief one-line description.
    
    Longer description with details about behavior,
    edge cases, and important notes. Describe what
    the method does and when to use it.
    
    Args:
        param1: Description of param1 with type context
        param2: Description of param2 (optional, defaults to None)
    
    Returns:
        ReturnType: Description of return value structure and contents
    
    Raises:
        ValidationError: When param1 is invalid format or fails validation
        NotFoundError: When the requested resource doesn't exist
        PermissionDeniedError: When user lacks permission to perform action
        NetworkError: When external service communication fails
        RuntimeError: When SDK is not properly initialized
    
    Example:
        ```python
        result = await obj.method_name(
            param1="value",
            param2=42
        )
        print(result.id)
        ```
    
    Note:
        Additional important information, warnings, or caveats.
        Use this section sparingly for critical information.
    """
```

## Section Descriptions

### 1. Brief Description (Required)
- **One line only** - summarize what the method does
- Use imperative mood: "Get document by ID" not "Gets document by ID"
- Examples: "Upload a document", "Delete document version", "Check agent permissions"

### 2. Detailed Description (Optional but Recommended)
- Expand on the brief description with context
- Explain when and why to use this method
- Describe any important behavior or edge cases
- Keep it concise - 2-4 sentences usually sufficient

### 3. Args Section (Required if method has parameters)
- List each parameter with description
- Include type context even though types are in signature
- Mention default values if relevant to usage
- For complex parameters, describe structure:
  ```
  permissions: List of PermissionGrant objects containing:
      - agent_id: Agent UUID
      - permission: Permission level (READ, WRITE, etc.)
  ```

### 4. Returns Section (Required for non-None returns)
- State the return type (even though in signature)
- Describe the structure and contents of the return value
- For dict returns, list key fields
- For complex objects, describe important attributes

### 5. Raises Section (REQUIRED)
- **This is the most important section for v2.1**
- List ALL exceptions the method can raise
- Include brief description of WHEN each exception occurs
- Order by likelihood: most common first
- Standard exceptions to consider:
  - `ValidationError`: Invalid input parameters
  - `DocumentNotFoundError`: Document doesn't exist
  - `AgentNotFoundError`: Agent doesn't exist  
  - `OrganizationNotFoundError`: Organization doesn't exist
  - `PermissionDeniedError`: Insufficient permissions
  - `StorageError`: File storage/retrieval failure
  - `RuntimeError`: SDK initialization issues

### 6. Example Section (Required for Complex Methods)
- Show realistic, complete usage
- Use meaningful variable names
- Include context (setup if needed)
- Show actual return value usage
- For simple methods, this is optional

### 7. Note Section (Optional)
- Use sparingly - only for critical information
- Warnings about breaking changes
- Performance considerations
- Security implications

## Examples by Method Type

### Simple Getter Method

```python
async def get_organization(
    self,
    org_id: UUID | str
) -> Organization:
    """
    Get organization by ID.
    
    Args:
        org_id: Organization UUID (as UUID or string)
    
    Returns:
        Organization: The organization object with id, metadata, and timestamps
    
    Raises:
        ValidationError: If org_id is invalid UUID format
        OrganizationNotFoundError: If organization doesn't exist
        RuntimeError: If SDK is not initialized
    """
```

### Complex Method with Multiple Operations

```python
async def upload(
    self,
    file_input: str | bytes | BinaryIO,
    name: str,
    organization_id: str | UUID,
    agent_id: str | UUID,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    content_type: Optional[str] = None,
    filename: Optional[str] = None,
    prefix: Optional[str] = None,
    create_version: bool = True,
    change_description: Optional[str] = None,
) -> Document:
    """
    Upload a document or create new version if exists.
    
    Supports multiple input types: file path (str), text content (str),
    bytes, or binary stream (BinaryIO). If a document with the same
    name exists in the organization, creates a new version or replaces
    the current version based on create_version parameter.
    
    Args:
        file_input: File path, text content, bytes, or binary stream
        name: Document display name
        organization_id: Organization UUID or string
        agent_id: Agent UUID or string (uploader)
        description: Optional document description
        tags: Optional list of tags for categorization
        metadata: Optional custom metadata dictionary
        content_type: Optional MIME type (auto-detected if None)
        filename: Optional filename override
        prefix: Optional hierarchical prefix (e.g., '/reports/2025/')
        create_version: If True and document exists, create new version.
                       If False and document exists, replace current version.
        change_description: Description of changes (for versioning)
    
    Returns:
        Document: The uploaded/updated document with id, storage info,
                 version number, and metadata
    
    Raises:
        ValidationError: If file_input type is invalid or parameters fail validation
        OrganizationNotFoundError: If organization doesn't exist
        AgentNotFoundError: If agent doesn't exist
        StorageError: If file upload to storage backend fails
        PermissionDeniedError: If agent lacks WRITE permission (for updates)
        DocumentNotFoundError: If attempting to update non-existent document
        RuntimeError: If SDK is not initialized
    
    Example:
        ```python
        # Upload from file path
        doc = await vault.upload(
            file_input="/path/to/report.pdf",
            name="Q4 Report",
            organization_id=org_id,
            agent_id=agent_id,
            prefix="/reports/2025/q4/"
        )
        
        # Create new version
        doc_v2 = await vault.upload(
            file_input=updated_content,
            name="Q4 Report",  # Same name
            organization_id=org_id,
            agent_id=agent_id,
            create_version=True,
            change_description="Updated with final numbers"
        )
        ```
    
    Note:
        When create_version=False, previous version history is lost.
        Use create_version=True to maintain audit trail.
    """
```

### Method with Security Implications

```python
async def set_permissions(
    self,
    document_id: str | UUID,
    permissions: List[PermissionGrant] | List[dict],
    granted_by: str | UUID,
) -> List[Any]:
    """
    Set permissions for a document in bulk.
    
    Replaces all existing permissions with the provided list.
    Only agents with ADMIN permission can manage permissions.
    
    Args:
        document_id: Document UUID or string
        permissions: List of PermissionGrant objects or dicts with:
            - agent_id: UUID or string
            - permission: Permission level (READ, WRITE, DELETE, SHARE, ADMIN)
            - expires_at: Optional expiration datetime
            - metadata: Optional custom metadata
        granted_by: UUID or string of agent granting permissions
    
    Returns:
        List[DocumentACL]: Created/updated permission records
    
    Raises:
        ValidationError: If permission data is invalid or permission level unknown
        DocumentNotFoundError: If document doesn't exist
        AgentNotFoundError: If granting agent or target agent doesn't exist
        PermissionDeniedError: If granting agent lacks ADMIN permission
        RuntimeError: If SDK is not initialized
    
    Example:
        ```python
        from doc_vault.database.schemas import PermissionGrant
        
        await vault.set_permissions(
            document_id=doc_id,
            permissions=[
                PermissionGrant(agent_id=agent1, permission="READ"),
                PermissionGrant(agent_id=agent2, permission="WRITE"),
            ],
            granted_by=admin_id
        )
        ```
    
    Note:
        This operation REPLACES all existing permissions. To add permissions
        while preserving existing ones, first get current permissions and
        merge with new ones before calling this method.
    """
```

## Exception Documentation Rules

### 1. Always Document These
- `RuntimeError` if method requires SDK initialization
- `ValidationError` for any parameter validation
- `*NotFoundError` for any entity lookups
- `PermissionDeniedError` for permission-protected operations

### 2. When to Include StorageError
- Any method that reads/writes to storage backend
- `upload()`, `download()`, `delete()`, version operations

### 3. When to Include PermissionDeniedError
- Methods that check permissions before acting
- Document updates, deletions, permission management
- Any operation that requires specific permission level

### 4. Order of Exceptions in Raises
1. Parameter validation errors (ValidationError)
2. Entity not found errors (DocumentNotFoundError, AgentNotFoundError, etc.)
3. Permission/authorization errors (PermissionDeniedError)
4. External service errors (StorageError)
5. System errors (RuntimeError)

## Checklist for New Methods

Before committing a new method, verify:

- [ ] Brief description is one line and imperative mood
- [ ] Detailed description explains when/why to use
- [ ] All parameters documented in Args
- [ ] Return value structure described
- [ ] **ALL possible exceptions listed in Raises with when/why**
- [ ] Example provided for complex methods (3+ parameters)
- [ ] Note section used only if critical information exists
- [ ] Docstring follows Google/NumPy style
- [ ] No typos or grammar errors

## Tools for Validation

```bash
# Check docstring completeness
ruff check src/doc_vault/core.py --select D

# Validate docstring format
pydocstyle src/doc_vault/core.py

# Generate documentation
pdoc doc_vault
```

## Migration from v2.0 to v2.1

When updating existing methods:

1. **Keep existing Args/Returns sections** - don't change unless parameters changed
2. **Add Raises section** - this is the main addition for v2.1
3. **Review Examples** - update if API changed
4. **Add Note section** - only if breaking change or security implication

## Common Mistakes to Avoid

1. ❌ **Forgetting RuntimeError**: All SDK methods can raise this
2. ❌ **Missing ValidationError**: Almost all methods validate parameters
3. ❌ **Incomplete Raises**: Listing only some exceptions
4. ❌ **Vague descriptions**: "When something goes wrong" - be specific!
5. ❌ **No examples for complex methods**: Users need guidance
6. ❌ **Overusing Note section**: Only for critical information

## Good vs Bad Examples

### ❌ Bad: Missing Raises

```python
async def delete(self, document_id: str | UUID, agent_id: str | UUID) -> None:
    """
    Delete a document.
    
    Args:
        document_id: Document UUID
        agent_id: Agent UUID
    """
```

### ✅ Good: Complete Raises

```python
async def delete(self, document_id: str | UUID, agent_id: str | UUID) -> None:
    """
    Delete a document.
    
    Marks document as deleted. Use hard_delete=True to permanently remove.
    
    Args:
        document_id: Document UUID or string
        agent_id: Agent UUID or string (requester)
    
    Raises:
        ValidationError: If UUIDs are invalid format
        DocumentNotFoundError: If document doesn't exist
        AgentNotFoundError: If agent doesn't exist
        PermissionDeniedError: If agent lacks DELETE permission
        StorageError: If file removal from storage fails
        RuntimeError: If SDK is not initialized
    """
```

---

**Last Updated**: November 21, 2025 (v2.1)
