#!/usr/bin/env python3
"""
Migration script to move Instance.key to InstanceKey table.

This script should be run BEFORE dropping the 'key' column from instances table.
It reads all existing instances with their keys and creates corresponding InstanceKey records.

Usage:
    python scripts/migrate_instance_keys.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import db
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def migrate_instance_keys():
    """Migrate existing Instance.key values to InstanceKey table"""

    logger.info("Starting instance keys migration...")

    try:
        # Initialize database connection
        await db.init_db()

        async with db.session() as session:
            # Check if 'key' column still exists in instances table
            check_column_sql = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'instances'
                AND column_name = 'key'
            """)
            result = await session.execute(check_column_sql)
            has_key_column = result.scalar_one_or_none() is not None

            if not has_key_column:
                logger.warning("Column 'key' does not exist in 'instances' table. Migration may have already been run.")
                logger.info("Checking if instance_keys table has data...")

                count_sql = text("SELECT COUNT(*) FROM instance_keys")
                result = await session.execute(count_sql)
                count = result.scalar()
                logger.info(f"Found {count} records in instance_keys table")
                return

            # Read all instances with their keys
            select_sql = text("""
                SELECT id, key
                FROM instances
                WHERE key IS NOT NULL
            """)
            result = await session.execute(select_sql)
            instances = result.fetchall()

            if not instances:
                logger.info("No instances with keys found. Nothing to migrate.")
                return

            logger.info(f"Found {len(instances)} instances to migrate")

            # Create InstanceKey records for each instance
            migrated_count = 0
            skipped_count = 0

            for instance_id, key in instances:
                try:
                    # Check if key already exists in instance_keys
                    check_sql = text("""
                        SELECT id FROM instance_keys
                        WHERE instance_id = :instance_id OR key = :key
                    """)
                    result = await session.execute(
                        check_sql,
                        {"instance_id": instance_id, "key": key}
                    )
                    existing = result.fetchone()

                    if existing:
                        logger.warning(f"InstanceKey already exists for instance {instance_id} or key '{key}', skipping")
                        skipped_count += 1
                        continue

                    # Insert new InstanceKey record
                    insert_sql = text("""
                        INSERT INTO instance_keys (id, instance_id, key, created_at)
                        VALUES (gen_random_uuid(), :instance_id, :key, NOW())
                    """)
                    await session.execute(
                        insert_sql,
                        {"instance_id": instance_id, "key": key}
                    )

                    migrated_count += 1
                    logger.info(f"Migrated: instance {instance_id} -> key '{key}'")

                except Exception as e:
                    logger.error(f"Error migrating instance {instance_id} with key '{key}': {e}")
                    raise

            # Commit all changes
            await session.commit()

            logger.info(f"Migration completed successfully!")
            logger.info(f"  - Migrated: {migrated_count}")
            logger.info(f"  - Skipped: {skipped_count}")
            logger.info(f"  - Total: {len(instances)}")

            # Show next steps
            logger.info("\nNext steps:")
            logger.info("1. Verify the data in instance_keys table")
            logger.info("2. Run: ALTER TABLE instances DROP COLUMN key;")
            logger.info("3. Restart the application")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        await db.close()


async def verify_migration():
    """Verify the migration by comparing counts"""
    logger.info("\nVerifying migration...")

    try:
        await db.init_db()

        async with db.session() as session:
            # Count instances with keys (if column exists)
            check_column_sql = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'instances'
                AND column_name = 'key'
            """)
            result = await session.execute(check_column_sql)
            has_key_column = result.scalar_one_or_none() is not None

            if has_key_column:
                count_instances_sql = text("""
                    SELECT COUNT(*) FROM instances WHERE key IS NOT NULL
                """)
                result = await session.execute(count_instances_sql)
                instances_count = result.scalar()
                logger.info(f"Instances with keys: {instances_count}")

            # Count instance_keys
            count_keys_sql = text("SELECT COUNT(*) FROM instance_keys")
            result = await session.execute(count_keys_sql)
            keys_count = result.scalar()
            logger.info(f"Instance keys: {keys_count}")

            if has_key_column and instances_count == keys_count:
                logger.info("✓ Migration verified successfully!")
            elif not has_key_column:
                logger.info(f"✓ Column 'key' has been dropped. Found {keys_count} instance keys.")
            else:
                logger.warning(f"⚠ Mismatch: {instances_count} instances vs {keys_count} keys")

    except Exception as e:
        logger.error(f"Verification failed: {e}")
    finally:
        await db.close()


async def main():
    """Main entry point"""
    logger.info("Instance Keys Migration Tool")
    logger.info("=" * 50)

    await migrate_instance_keys()
    await verify_migration()

    logger.info("\nMigration process completed!")


if __name__ == "__main__":
    asyncio.run(main())
