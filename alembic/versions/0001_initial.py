"""initial migration

Revision ID: 0001
Revises:
Create Date: 2024-05-20 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False, unique=True),
        sa.Column('status', sa.String(), default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now())
    )
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('role', sa.String(), default='USER'),
        sa.Column('status', sa.String(), default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now())
    )
    op.create_table('rooms',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', sa.String(), default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now())
    )
    op.create_table('room_members',
        sa.Column('room_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rooms.id'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('role', sa.String(), default='PARTICIPANT'),
        sa.Column('presence', sa.String(), default='OFFLINE'),
        sa.Column('is_muted', sa.Boolean(), default=False),
        sa.Column('is_approved', sa.Boolean(), default=True),
        sa.Column('joined_at', sa.DateTime(), default=sa.func.now())
    )
    op.create_table('sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('refresh_token_hash', sa.String(), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True)
    )

def downgrade():
    op.drop_table('sessions')
    op.drop_table('room_members')
    op.drop_table('rooms')
    op.drop_table('users')
    op.drop_table('tenants')
