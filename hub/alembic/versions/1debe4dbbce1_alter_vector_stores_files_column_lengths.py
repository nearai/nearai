"""alter_vector_stores_files_column_lengths.

Revision ID: 1debe4dbbce1
Revises: e8c084b2232b
Create Date: 2025-03-03 16:20:48.585525

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1debe4dbbce1"
down_revision: Union[str, None] = "e8c084b2232b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create a new table with the updated structure
    op.execute("""
    CREATE TABLE vector_store_files_new (
        id VARCHAR(64) PRIMARY KEY,
        account_id VARCHAR(64) NOT NULL,
        file_uri VARCHAR(1024) NOT NULL,
        purpose VARCHAR(50) NOT NULL,
        filename VARCHAR(1024) NOT NULL,
        content_type VARCHAR(100) NOT NULL,
        file_size INT NOT NULL,
        encoding VARCHAR(20),
        embedding_status VARCHAR(20),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=columnstore;
    """)

    # 2. Create the index on the new table
    op.execute("""
    CREATE INDEX idx_vector_store_files_account_id ON vector_store_files_new (account_id);
    """)

    # 3. Copy data from the old table to the new one
    op.execute("""
    INSERT INTO vector_store_files_new
    SELECT * FROM vector_store_files;
    """)

    # 4. Drop the old table
    op.execute("""
    DROP TABLE vector_store_files;
    """)

    # 5. Rename the new table to the original name
    op.execute("""
    ALTER TABLE vector_store_files_new RENAME TO vector_store_files;
    """)


def downgrade() -> None:
    # Reverse procedure: create a table with the original field lengths
    op.execute("""
    CREATE TABLE vector_store_files_old (
        id VARCHAR(64) PRIMARY KEY,
        account_id VARCHAR(64) NOT NULL,
        file_uri VARCHAR(255) NOT NULL,
        purpose VARCHAR(50) NOT NULL,
        filename VARCHAR(255) NOT NULL,
        content_type VARCHAR(100) NOT NULL,
        file_size INT NOT NULL,
        encoding VARCHAR(20),
        embedding_status VARCHAR(20),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=columnstore;
    """)

    # Create the index
    op.execute("""
    CREATE INDEX idx_vector_store_files_account_id ON vector_store_files_old (account_id);
    """)

    # Copy data (with the risk of truncating values that are too long)
    op.execute("""
    INSERT INTO vector_store_files_old
    SELECT id, account_id, LEFT(file_uri, 255), purpose, LEFT(filename, 255),
           content_type, file_size, encoding, embedding_status, created_at, updated_at
    FROM vector_store_files;
    """)

    # Drop the new table
    op.execute("""
    DROP TABLE vector_store_files;
    """)

    # Rename the old table back to the original name
    op.execute("""
    ALTER TABLE vector_store_files_old RENAME TO vector_store_files;
    """)
