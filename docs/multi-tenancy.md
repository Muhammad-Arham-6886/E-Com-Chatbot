# Authentication & Multi-Tenancy Design

## Authentication Design
The platform uses JWT (JSON Web Tokens) with standard Bearer authorization headers:
1. **Password Hashing**: Bcrypt with salted rounds.
2. **Access Tokens**: Encoded with user ID, email, expiration, and signed with HMAC-SHA256 using `SECRET_KEY`.
3. **Session Verification**: `get_current_user` FastAPI dependency decodes the Bearer token, checks user validity and active status against the database.

## Multi-Tenancy Architecture
Multi-tenancy is structured as:
```
User -> OrganizationMember -> Organization -> Websites
```

### Tenant Isolation Rules
1. **Never trust client-supplied tenant identifiers**: All API requests affecting an organization must pass through authorization checks verifying that the authenticated user is an active member of that organization.
2. **Role-Based Access Control (RBAC)**:
   - `OWNER`: Full control, billing, organization deletion, member management.
   - `ADMIN`: Full configuration, adding/removing members (except OWNER), managing websites.
   - `MANAGER`: Manage website knowledge, view analytics, manage integrations.
   - `AGENT`: View and respond to conversations, view products.
   - `VIEWER`: Read-only access to analytics and settings.
3. **Cross-Tenant Attack Prevention**:
   Querying `/api/v1/organizations/{org_id}` validates `organization_id` against `organization_members` for the logged-in user. If the user does not belong to `org_id`, the system returns `403 Forbidden` or `404 Not Found`.
