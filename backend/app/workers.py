import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete

from app.database import db
from app.models.email import Email
from app.services.email_parser import EmailParserService
from app.config import settings

logger = logging.getLogger(__name__)

# Run the retention sweep at most this often (seconds), independent of POLL_INTERVAL.
_RETENTION_SWEEP_INTERVAL = 3600


class EmailMonitorWorker:
    """Background worker that monitors Maildir for new emails"""

    def __init__(self):
        self.running = False
        self.processed_files = set()
        self._last_retention_sweep = 0.0

    async def start(self):
        """Start the email monitoring worker"""
        self.running = True
        logger.info("Email monitor worker started")

        # NOTE: we deliberately do NOT pre-mark existing Maildir files as processed.
        # On startup we (re)scan everything; save_email is idempotent via the unique
        # message_id, so already-ingested mail is skipped while genuinely new mail that
        # arrived while we were down (or after a DB restore) is still picked up.
        # `processed_files` is only an in-process fast-path, not a durability mechanism.

        # Start monitoring loop
        while self.running:
            try:
                await self._check_for_new_emails()
                await self._maybe_purge_old_emails()
                await asyncio.sleep(settings.POLL_INTERVAL)
            except Exception as e:
                logger.error(f"Error in email monitor worker: {e}")
                await asyncio.sleep(settings.POLL_INTERVAL)

    async def _maybe_purge_old_emails(self):
        """Delete emails older than EMAIL_RETENTION_DAYS (0 = keep forever)."""
        days = settings.EMAIL_RETENTION_DAYS
        if days <= 0:
            return
        now = time.monotonic()
        if now - self._last_retention_sweep < _RETENTION_SWEEP_INTERVAL:
            return
        self._last_retention_sweep = now
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        try:
            async with db.session() as session:
                result = await session.execute(
                    delete(Email).where(Email.received_at < cutoff)
                )
            if result.rowcount:
                logger.info(f"Retention sweep: deleted {result.rowcount} emails older than {days}d")
        except Exception as e:
            logger.error(f"Error during retention sweep: {e}")

    async def stop(self):
        """Stop the email monitoring worker"""
        self.running = False
        logger.info("Email monitor worker stopped")

    async def _check_for_new_emails(self):
        """Check for new email files and process them"""
        try:
            maildir_path = Path(settings.MAILDIR_PATH)
            if not maildir_path.exists():
                return

            # Find new files
            new_files = []
            for file_path in maildir_path.glob('*'):
                if file_path.is_file() and file_path.name not in self.processed_files:
                    new_files.append(file_path)

            if not new_files:
                return

            logger.info(f"Found {len(new_files)} new email file(s)")

            # Process new emails
            async with db.session() as session:
                for file_path in new_files:
                    try:
                        email_data = EmailParserService.parse_email_file(str(file_path))
                        if email_data:
                            email = await EmailParserService.save_email(session, email_data)
                            if email:
                                self.processed_files.add(file_path.name)
                                logger.info(f"Processed new email: {file_path.name}")
                        else:
                            # Mark as processed even if parsing failed to avoid repeated attempts
                            self.processed_files.add(file_path.name)
                            logger.warning(f"Failed to parse email: {file_path.name}")
                    except Exception as e:
                        logger.error(f"Error processing email {file_path.name}: {e}")
                        # Don't mark as processed if there was an error, will retry next time

        except Exception as e:
            logger.error(f"Error checking for new emails: {e}")


# Global worker instance
email_monitor = EmailMonitorWorker()
