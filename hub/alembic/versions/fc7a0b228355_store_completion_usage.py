"""Store completion usage.

Revision ID: fc7a0b228355
Revises: 1debe4dbbce1
Create Date: 2025-03-11 21:22:43.764049

"""

import json
import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import LONGTEXT

# revision identifiers, used by Alembic.
revision: str = "fc7a0b228355"
down_revision: Union[str, None] = "1debe4dbbce1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def extract_usage_data(response: str) -> dict:
    """Extract usage data from response string with robust error handling.

    Handles cases where single quotes were escaped with '' during storage.

    Args:
    ----
        response: The raw response string from the database

    Returns:
    -------
        Dictionary containing token usage information

    """
    # Default values if extraction fails
    default_usage = {
        "completion_tokens": 0,
        "prompt_tokens": 0,
        "total_tokens": 0,
        "completion_tokens_details": None,
        "prompt_tokens_details": None,
    }

    try:
        # Method 1: Direct JSON parsing after fixing doubled single quotes
        # Convert '' back to ' for proper JSON parsing
        fixed_response = response.replace("''", "'")
        data = json.loads(fixed_response)
        if "usage" in data:
            return data["usage"]

    except json.JSONDecodeError:
        # Continue to fallback methods if direct parsing fails
        pass

    try:
        # Method 2: Regex-based extraction specifically for the usage object
        usage_pattern = r'"usage"\s*:\s*({[^}]*})'
        usage_match = re.search(usage_pattern, response)

        if usage_match:
            usage_str = usage_match.group(1)
            # Fix doubled quotes in the usage string
            usage_str = usage_str.replace("''", "'")
            return json.loads(usage_str)

    except (json.JSONDecodeError, AttributeError):
        # Continue to next fallback method
        pass

    # Method 3: Extract individual token values with regex
    try:
        completion_tokens = (
            int(re.search(r'"completion_tokens"\s*:\s*(\d+)', response).group(1))  # type: ignore
            if re.search(r'"completion_tokens"\s*:\s*(\d+)', response)
            else 0
        )
        prompt_tokens = (
            int(re.search(r'"prompt_tokens"\s*:\s*(\d+)', response).group(1))  # type: ignore
            if re.search(r'"prompt_tokens"\s*:\s*(\d+)', response)
            else 0
        )
        total_tokens = (
            int(re.search(r'"total_tokens"\s*:\s*(\d+)', response).group(1))  # type: ignore
            if re.search(r'"total_tokens"\s*:\s*(\d+)', response)
            else 0
        )

        # If we successfully extracted at least one value, return a usage object
        if completion_tokens > 0 or prompt_tokens > 0 or total_tokens > 0:
            return {
                "completion_tokens": completion_tokens,
                "prompt_tokens": prompt_tokens,
                "total_tokens": total_tokens,
                "completion_tokens_details": None,
                "prompt_tokens_details": None,
            }
    except (AttributeError, ValueError):
        # Final fallback - return default values
        pass

    return default_usage


def upgrade() -> None:
    # Get database connection
    conn = op.get_bind()

    # Step 1: Add new nullable columns to existing table
    op.add_column("completions", sa.Column("completion_tokens", sa.Integer(), nullable=True))
    op.add_column("completions", sa.Column("prompt_tokens", sa.Integer(), nullable=True))
    op.add_column("completions", sa.Column("total_tokens", sa.Integer(), nullable=True))
    op.add_column("completions", sa.Column("completion_tokens_details", sa.JSON(), nullable=True))
    op.add_column("completions", sa.Column("prompt_tokens_details", sa.JSON(), nullable=True))

    # Step 2: Fetch all records that need processing
    print("Fetching records for processing...")
    rows = conn.execute(sa.text("SELECT id, response FROM completions")).fetchall()

    total_records = len(rows)
    print(f"Found {total_records} records to process")

    # Step 3: Process each record with robust error handling
    success_count = 0
    error_count = 0
    error_ids = []

    batch_size = 1000
    total_batches = (total_records + batch_size - 1) // batch_size

    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = (batch_idx + 1) * batch_size
        batch = rows[start_idx:end_idx]

        batch_updates = []
        batch_error_ids = []

        for row in batch:
            row_id = row.id
            response_text = row.response

            try:
                usage_data = extract_usage_data(response_text)
                update_values = {
                    "id": row_id,
                    "ct": usage_data.get("completion_tokens", 0),
                    "pt": usage_data.get("prompt_tokens", 0),
                    "tt": usage_data.get("total_tokens", 0),
                    "ctd": json.dumps(usage_data.get("completion_tokens_details"))
                    if usage_data.get("completion_tokens_details")
                    else None,
                    "ptd": json.dumps(usage_data.get("prompt_tokens_details"))
                    if usage_data.get("prompt_tokens_details")
                    else None,
                }

                if update_values["tt"] == 0:
                    update_values["tt"] = update_values["ct"] + update_values["pt"]

                batch_updates.append(update_values)

            except Exception as e:
                error_count += 1
                batch_error_ids.append(row_id)
                print(f"Error processing record {row_id}: {str(e)}")
                print(f"Problematic response snippet: {response_text[:100]}...")

        if batch_updates:
            try:
                # Batch update using executemany
                conn.execute(
                    sa.text("""
                        UPDATE completions
                        SET completion_tokens = :ct,
                            prompt_tokens = :pt,
                            total_tokens = :tt,
                            completion_tokens_details = :ctd,
                            prompt_tokens_details = :ptd
                        WHERE id = :id
                    """),
                    batch_updates,  # List of updates in a batch
                )

                success_count += len(batch_updates)

            except Exception as e:
                error_count += len(batch_updates)
                batch_error_ids.extend([u["id"] for u in batch_updates])
                print(f"Batch {batch_idx + 1} failed: {str(e)}")

        error_ids.extend(batch_error_ids)

        # Progress update
        processed = min(end_idx, total_records)
        print(
            f"Processed batch {batch_idx + 1}/{total_batches} "
            f"({processed}/{total_records}, {processed / total_records:.1%})"
        )

    # Print summary statistics
    print("\nMigration Summary:")
    print(f"Total records processed: {total_records}")
    print(f"Successful updates: {success_count}")
    print(f"Failed updates: {error_count}")
    if error_count > 0:
        print(f"First 10 error IDs: {error_ids[:10]}")

    # Step 4: Create new table with proper schema constraints
    print("\nCreating new table with updated schema...")

    op.create_table(
        "new_completions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True, nullable=False),
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column("query", LONGTEXT, nullable=False),
        sa.Column("response", LONGTEXT, nullable=False),
        sa.Column("model", sa.Text, nullable=False),
        sa.Column("provider", sa.Text, nullable=False),
        sa.Column("endpoint", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP, nullable=False, server_default=sa.func.current_timestamp()),
        # New columns with NOT NULL constraints and defaults
        sa.Column("completion_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("prompt_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completion_tokens_details", sa.JSON, nullable=True),
        sa.Column("prompt_tokens_details", sa.JSON, nullable=True),
        # SingleStore specific configuration
        sa.Index("completions_account_id_idx", "account_id"),
        sa.Index("idx_account_created", "account_id", "created_at"),
        sa.Index(
            "idx_account_created_cover",
            "account_id",
            "created_at",
            "completion_tokens",
            "prompt_tokens",
            "total_tokens",
        ),
        mysql_charset="utf8mb4",  # Character set
        mysql_collate="utf8mb4_unicode_ci",  # Collation
    )

    # Step 5: Migrate data to new table structure
    print("Migrating data to new table structure...")
    conn.execute(
        sa.text("""
        INSERT INTO new_completions
        SELECT
            id, account_id, query, response, model, provider, endpoint, created_at,
            IFNULL(completion_tokens, 0),
            IFNULL(prompt_tokens, 0),
            IFNULL(total_tokens, 0),
            completion_tokens_details,
            prompt_tokens_details
        FROM completions
    """)
    )

    # CRITICAL! Enable auto-increment sync for SingleStore
    conn.execute(sa.text("AGGREGATOR SYNC AUTO_INCREMENT"))

    # Step 6: Replace old table with new structure
    print("Replacing old table with new structure...")
    op.drop_table("completions")
    op.rename_table("new_completions", "completions")

    print("Migration completed successfully!")


def downgrade() -> None:
    # Remove the added columns for rollback
    print("Downgrading - removing added columns...")
    op.drop_column("completions", "completion_tokens")
    op.drop_column("completions", "prompt_tokens")
    op.drop_column("completions", "total_tokens")
    op.drop_column("completions", "completion_tokens_details")
    op.drop_column("completions", "prompt_tokens_details")
    print("Downgrade completed")
