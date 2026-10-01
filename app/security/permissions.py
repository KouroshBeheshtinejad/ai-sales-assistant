STORE_PERMISSIONS = frozenset(
    {
        "store.read",
        "store.update",
        "store.delete",
        "product.read",
        "product.create",
        "product.update",
        "product.delete",
        "order.read",
        "order.update",
        "order.cancel",
        "conversation.read",
        "conversation.create",
        "conversation.reply",
        "knowledge.read",
        "knowledge.write",
        "faq.read",
        "faq.write",
        "member.read",
        "member.invite",
        "member.approve",
        "member.update",
        "member.remove",
        "support.contact",
        "billing.read",
        "billing.manage",
        "analytics.read",
    }
)

STORE_ROLE_PERMISSIONS = {
    "store_admin": STORE_PERMISSIONS,
    "store_manager": frozenset(
        {
            "store.read",
            "product.read",
            "product.create",
            "product.update",
            "order.read",
            "order.update",
            "conversation.read",
            "knowledge.read",
            "knowledge.write",
            "faq.read",
            "faq.write",
            "analytics.read",
            "support.contact",
        }
    ),
    "store_viewer": frozenset(
        {
            "store.read",
            "product.read",
            "order.read",
            "conversation.read",
            "knowledge.read",
            "faq.read",
            "analytics.read",
            "support.contact",
        }
    ),
}


def roles_with_permission(permission: str) -> tuple[str, ...]:
    if permission not in STORE_PERMISSIONS:
        return ()
    return tuple(
        role
        for role, permissions in STORE_ROLE_PERMISSIONS.items()
        if permission in permissions
    )