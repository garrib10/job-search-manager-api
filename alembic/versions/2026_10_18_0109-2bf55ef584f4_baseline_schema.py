"""baseline schema

Revision ID: 2bf55ef584f4
Revises:
Create Date: 2026-10-18 01:09:47.022136

The schema as it existed before Alembic, when tables were created by
Base.metadata.create_all(): companies, users, job_applications, interviews,
with their indexes, unique constraints, and foreign keys.

Existing databases created by create_all() should be stamped at this
revision (`alembic stamp 2bf55ef584f4`) after a backup and schema comparison,
not upgraded. See docs/database-migrations.md.

WARNING: downgrading this revision drops every table and all data in them.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2bf55ef584f4'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('companies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('website', sa.String(length=255), nullable=True),
    sa.Column('industry', sa.String(length=100), nullable=True),
    sa.Column('location', sa.String(length=150), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_companies_id'), 'companies', ['id'], unique=False)
    op.create_index(op.f('ix_companies_location'), 'companies', ['location'], unique=False)
    op.create_index(op.f('ix_companies_name'), 'companies', ['name'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('job_applications',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('job_title', sa.String(length=200), nullable=False),
    sa.Column('location', sa.String(length=150), nullable=True),
    sa.Column('work_arrangement', sa.Enum('remote', 'hybrid', 'onsite', name='workarrangement'), nullable=True),
    sa.Column('status', sa.Enum('saved', 'applied', 'interviewing', 'offer', 'rejected', 'withdrawn', name='applicationstatus'), nullable=False),
    sa.Column('salary_min', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('salary_max', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('job_url', sa.String(length=500), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('date_saved', sa.Date(), nullable=False),
    sa.Column('date_applied', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('job_url')
    )
    op.create_index(op.f('ix_job_applications_company_id'), 'job_applications', ['company_id'], unique=False)
    op.create_index(op.f('ix_job_applications_job_title'), 'job_applications', ['job_title'], unique=False)
    op.create_index(op.f('ix_job_applications_location'), 'job_applications', ['location'], unique=False)
    op.create_index(op.f('ix_job_applications_status'), 'job_applications', ['status'], unique=False)
    op.create_index(op.f('ix_job_applications_work_arrangement'), 'job_applications', ['work_arrangement'], unique=False)
    op.create_table('interviews',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('interview_type', sa.Enum('phone_screen', 'technical', 'behavioral', 'hiring_manager', 'onsite', 'virtual_onsite', 'final', 'hr', 'other', name='interviewtype'), nullable=False),
    sa.Column('status', sa.Enum('scheduled', 'completed', 'cancelled', 'rescheduled', name='interviewstatus'), nullable=False),
    sa.Column('outcome', sa.Enum('pending', 'advanced', 'rejected', 'offer', 'withdrawn', name='interviewoutcome'), nullable=False),
    sa.Column('scheduled_at', sa.DateTime(), nullable=False),
    sa.Column('interviewer', sa.String(length=150), nullable=True),
    sa.Column('location', sa.String(length=150), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('application_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['application_id'], ['job_applications.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_interviews_application_id'), 'interviews', ['application_id'], unique=False)
    op.create_index(op.f('ix_interviews_interview_type'), 'interviews', ['interview_type'], unique=False)
    op.create_index(op.f('ix_interviews_outcome'), 'interviews', ['outcome'], unique=False)
    op.create_index(op.f('ix_interviews_status'), 'interviews', ['status'], unique=False)


def downgrade() -> None:
    """Drop all tables. Destroys all data; for local or disposable databases only."""
    # WHY:
    # Tables are dropped directly, children first. Dropping each index
    # separately fails on MySQL, which refuses to drop an index that a foreign
    # key depends on (error 1553). Dropping a table removes its indexes too.
    op.drop_table("interviews")
    op.drop_table("job_applications")
    op.drop_table("users")
    op.drop_table("companies")
