"""003_crawling_and_documents

Revision ID: 003
Revises: 002
Create Date: 2026-08-19 21:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Crawl Jobs table
    op.create_table(
        'crawl_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('website_id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', name='crawljobstatusenum'), nullable=False),
        sa.Column('total_pages_discovered', sa.Integer(), nullable=False, default=0),
        sa.Column('total_pages_crawled', sa.Integer(), nullable=False, default=0),
        sa.Column('total_pages_failed', sa.Integer(), nullable=False, default=0),
        sa.Column('max_pages', sa.Integer(), nullable=False, default=50),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['website_id'], ['websites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_crawl_jobs_id'), 'crawl_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_crawl_jobs_organization_id'), 'crawl_jobs', ['organization_id'], unique=False)
    op.create_index(op.f('ix_crawl_jobs_website_id'), 'crawl_jobs', ['website_id'], unique=False)
    op.create_index(op.f('ix_crawl_jobs_status'), 'crawl_jobs', ['status'], unique=False)

    # Crawl Pages table
    op.create_table(
        'crawl_pages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('crawl_job_id', sa.String(length=36), nullable=False),
        sa.Column('website_id', sa.String(length=36), nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('status', sa.Enum('DISCOVERED', 'CRAWLED', 'SKIPPED_ROBOTS', 'FAILED', 'DUPLICATE', name='crawlpagestatusenum'), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('page_title', sa.String(length=512), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('discovered_via', sa.String(length=64), nullable=False, default='sitemap'),
        sa.Column('depth', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['crawl_job_id'], ['crawl_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['website_id'], ['websites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_crawl_pages_id'), 'crawl_pages', ['id'], unique=False)
    op.create_index(op.f('ix_crawl_pages_crawl_job_id'), 'crawl_pages', ['crawl_job_id'], unique=False)
    op.create_index(op.f('ix_crawl_pages_website_id'), 'crawl_pages', ['website_id'], unique=False)
    op.create_index(op.f('ix_crawl_pages_url'), 'crawl_pages', ['url'], unique=False)
    op.create_index(op.f('ix_crawl_pages_status'), 'crawl_pages', ['status'], unique=False)
    op.create_index(op.f('ix_crawl_pages_content_hash'), 'crawl_pages', ['content_hash'], unique=False)

    # Knowledge Documents table
    op.create_table(
        'knowledge_documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('website_id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('crawl_page_id', sa.String(length=36), nullable=True),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('meta_description', sa.Text(), nullable=True),
        sa.Column('raw_content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False, default=0),
        sa.Column('status', sa.Enum('RAW', 'PROCESSED', 'SYNCED', name='documentstatusenum'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['crawl_page_id'], ['crawl_pages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['website_id'], ['websites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_documents_id'), 'knowledge_documents', ['id'], unique=False)
    op.create_index(op.f('ix_knowledge_documents_organization_id'), 'knowledge_documents', ['organization_id'], unique=False)
    op.create_index(op.f('ix_knowledge_documents_website_id'), 'knowledge_documents', ['website_id'], unique=False)
    op.create_index(op.f('ix_knowledge_documents_url'), 'knowledge_documents', ['url'], unique=False)
    op.create_index(op.f('ix_knowledge_documents_content_hash'), 'knowledge_documents', ['content_hash'], unique=False)


def downgrade() -> None:
    op.drop_table('knowledge_documents')
    op.drop_table('crawl_pages')
    op.drop_table('crawl_jobs')
    op.execute('DROP TYPE IF EXISTS crawljobstatusenum')
    op.execute('DROP TYPE IF EXISTS crawlpagestatusenum')
    op.execute('DROP TYPE IF EXISTS documentstatusenum')
