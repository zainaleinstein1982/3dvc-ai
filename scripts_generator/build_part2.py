import os

FILES = {
    "3dvc/alembic.ini": """[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://threedvc:devpassword@localhost:5432/threedvc_db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
""",
    "3dvc/alembic/env.py": """import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool
from alembic import context
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app.db.database import Base
from app.db import models

config = context.config
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", "postgresql+asyncpg://threedvc:devpassword@localhost:5432/threedvc_db"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_online():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async def do_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
        await connectable.dispose()

    asyncio.run(do_migrations())

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

run_migrations_online()
""",
    "3dvc/alembic/script.py.mako": """\"\"\"${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
\"\"\"
from alembic import op
import sqlalchemy as sa
 ${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

def upgrade():
    ${upgrades if upgrades else "pass"}

def downgrade():
    ${downgrades if downgrades else "pass"}
""",
    "3dvc/alembic/versions/0001_initial.py": """\"\"\"initial migration

Revision ID: 0001
Revises:
Create Date: 2024-05-20 10:00:00.000000
\"\"\"
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
""",
    "3dvc/scripts/backup-postgres.sh": """#!/bin/bash
CONTAINER_NAME="3dvc-postgres"
DB_USER="threedvc"
DB_NAME="threedvc_db"
BACKUP_DIR="./backups"

mkdir -p $BACKUP_DIR
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

echo "Backing up $DB_NAME to $FILE..."
docker exec $CONTAINER_NAME pg_dump -U $DB_USER $DB_NAME | gzip > $FILE
echo "Backup complete."
""",
    "3dvc/scripts/restore-postgres.sh": """#!/bin/bash
CONTAINER_NAME="3dvc-postgres"
DB_USER="threedvc"
DB_NAME="threedvc_db"
FILE=$1

if [ -z "$FILE" ]; then
  echo "Please provide backup file path."
  exit 1
fi

echo "Restoring $FILE to $DB_NAME..."
gunzip -c $FILE | docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME
echo "Restore complete."
"""
}

def create_files():
    for filepath, content in FILES.items():
        full_path = os.path.join(os.getcwd(), filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        print(f"Created: {filepath}")

if __name__ == "__main__":
    create_files()
