import pytest
from httpx import AsyncClient
from app.models.enums import RoleEnum, MembershipStatus
from app.models.organization import OrganizationMember


@pytest.mark.asyncio
async def test_rbac_permissions_and_restrictions(
    client: AsyncClient, create_test_user, create_test_org, db_session
):
    # Setup Owner and Viewer in the same Organization
    owner, owner_token = await create_test_user("owner@example.com")
    viewer, viewer_token = await create_test_user("viewer@example.com")
    candidate, _ = await create_test_user("candidate@example.com")

    org = await create_test_org("Enterprise Org", owner)

    # Add viewer to org
    viewer_member = OrganizationMember(
        organization_id=org.id,
        user_id=viewer.id,
        role=RoleEnum.VIEWER,
        status=MembershipStatus.ACTIVE,
    )
    db_session.add(viewer_member)
    await db_session.commit()

    # 1. VIEWER can view organization
    res_view = await client.get(
        f"/api/v1/organizations/{org.id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res_view.status_code == 200

    # 2. VIEWER can list members
    res_members = await client.get(
        f"/api/v1/organizations/{org.id}/members",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res_members.status_code == 200
    assert len(res_members.json()) == 2

    # 3. VIEWER CANNOT invite members (requires ADMIN)
    res_invite = await client.post(
        f"/api/v1/organizations/{org.id}/members",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"email": "candidate@example.com", "role": "AGENT"},
    )
    assert res_invite.status_code == 403
    assert "requires at least" in res_invite.json()["detail"].lower()

    # 4. VIEWER CANNOT update org settings
    res_update = await client.put(
        f"/api/v1/organizations/{org.id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"name": "Attempted Name Change"},
    )
    assert res_update.status_code == 403

    # 5. OWNER CAN invite new member
    res_owner_invite = await client.post(
        f"/api/v1/organizations/{org.id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "candidate@example.com", "role": "MANAGER"},
    )
    assert res_owner_invite.status_code == 201
    assert res_owner_invite.json()["role"] == "MANAGER"

    # 6. OWNER CAN remove viewer
    res_remove = await client.delete(
        f"/api/v1/organizations/{org.id}/members/{viewer.id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res_remove.status_code == 200
