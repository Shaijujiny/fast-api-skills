"""organizations, roles, permissions, role_permissions, users.organization_id (+ default seed)

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# Snapshot of the defaults at the time of this migration (do not import app code into migrations).
_RESOURCES = ("users", "roles")
_ACTIONS = ("view", "create", "edit", "delete", "export")
_ALL = {(r, a) for r in _RESOURCES for a in _ACTIONS}
_ROLES = {
    "super_admin": ("Cross-tenant administrator", _ALL),
    "admin": ("Organization administrator", {("users", a) for a in _ACTIONS} | {("roles", "view")}),
    "staff": ("Read-only staff", {("users", "view")}),
    "user": ("Regular user, no admin access", set()),
}


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        *_ts(),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        sa.UniqueConstraint("public_id", name="uq_organizations_public_id"),
    )
    roles = op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(32), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        *_ts(),
        sa.PrimaryKeyConstraint("id", name="pk_roles"),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )
    permissions = op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resource", sa.String(64), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_permissions"),
        sa.UniqueConstraint("resource", "action", name="uq_permissions_resource_action"),
    )
    role_permissions = op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name="fk_role_permissions_role_id_roles", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            name="fk_role_permissions_permission_id_permissions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name="pk_role_permissions"),
    )

    perm_ids = {}
    for i, (resource, action) in enumerate(sorted(_ALL), start=1):
        op.bulk_insert(permissions, [{"id": i, "resource": resource, "action": action}])
        perm_ids[(resource, action)] = i
    for rid, (name, (description, pairs)) in enumerate(_ROLES.items(), start=1):
        op.bulk_insert(roles, [{"id": rid, "name": name, "description": description, "is_system": True}])
        op.bulk_insert(role_permissions, [{"role_id": rid, "permission_id": perm_ids[k]} for k in sorted(pairs)])

    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_users_organization_id_organizations", "organizations", ["organization_id"], ["id"], ondelete="RESTRICT"
        )
        batch.create_index("ix_users_organization_id", ["organization_id"])


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_organization_id")
        batch.drop_constraint("fk_users_organization_id_organizations", type_="foreignkey")
        batch.drop_column("organization_id")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("organizations")
