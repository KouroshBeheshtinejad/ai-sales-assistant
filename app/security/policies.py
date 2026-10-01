from sqlalchemy import false, or_, select, true
from sqlalchemy.orm import Session

from app.db.models import Store, StoreMembership, User
from app.security.permissions import STORE_PERMISSIONS, STORE_ROLE_PERMISSIONS, roles_with_permission


def store_scope_filter(user: User, permission: str = "store.read"):
    """Build a tenant scope predicate for one store permission."""
    if user.approval_status != "active" or permission not in STORE_PERMISSIONS:
        return false()
    if user.role == "god":
        return true()

    membership_roles = roles_with_permission(permission)
    if not membership_roles:
        return Store.owner_id == user.id

    approved_memberships = select(StoreMembership.store_id).where(
        StoreMembership.user_id == user.id,
        StoreMembership.status == "approved",
        StoreMembership.role.in_(membership_roles),
    )
    return or_(Store.owner_id == user.id, Store.id.in_(approved_memberships))


def has_store_permission(
    db: Session,
    user: User,
    store_id: int,
    permission: str,
) -> bool:
    if user.approval_status != "active" or permission not in STORE_PERMISSIONS:
        return False
    if user.role == "god":
        return True

    owner_id = db.scalar(select(Store.owner_id).where(Store.id == store_id))
    if owner_id is None:
        return False
    if owner_id == user.id:
        return True

    membership_roles = roles_with_permission(permission)
    if not membership_roles:
        return False
    membership_id = db.scalar(
        select(StoreMembership.id).where(
            StoreMembership.store_id == store_id,
            StoreMembership.user_id == user.id,
            StoreMembership.status == "approved",
            StoreMembership.role.in_(membership_roles),
        )
    )
    return membership_id is not None


def require_store_permission(
    db: Session,
    user: User,
    store_id: int,
    permission: str,
) -> None:
    from fastapi import HTTPException, status

    if not has_store_permission(db, user, store_id, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Store permission denied",
        )


def store_access(db: Session, user: User, store_id: int) -> dict | None:
    if user.approval_status != "active":
        return None
    if user.role == "god":
        return {"role": "god", "permissions": sorted(STORE_PERMISSIONS)}

    owner_id = db.scalar(select(Store.owner_id).where(Store.id == store_id))
    if owner_id is None:
        return None
    if owner_id == user.id:
        return {"role": "store_owner", "permissions": sorted(STORE_PERMISSIONS)}

    membership = db.scalar(
        select(StoreMembership).where(
            StoreMembership.store_id == store_id,
            StoreMembership.user_id == user.id,
            StoreMembership.status == "approved",
        )
    )
    if membership is None:
        return None
    return {
        "role": membership.role,
        "permissions": sorted(STORE_ROLE_PERMISSIONS.get(membership.role, ())),
    }