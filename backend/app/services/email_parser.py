import os
from email import message_from_file
from email.utils import parseaddr, parsedate_to_datetime
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import logging

import tldextract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.email import Email
from app.config import settings

logger = logging.getLogger(__name__)

# Offline extractor: use the bundled public-suffix snapshot, never hit the network.
_tld_extract = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)


class EmailParserService:
    """Service for parsing emails from Maildir and saving to database"""

    @staticmethod
    def parse_recipient(email_address: str) -> Optional[Tuple[str, str, bool]]:
        """
        Resolve a recipient address to a routing identity.

        Returns (routing_key, domain, is_bare) or None.
        - someone@KEY.acme.com -> ("KEY", "key.acme.com", False) -> routes by InstanceKey
        - someone@acme.com     -> ("acme.com", "acme.com", True) -> routes by verified InstanceDomain

        The public-suffix list is used to find the registrable domain, so this
        works for any domain (e.g. key.mypm.cloud, sub.acme.co.uk) without
        hard-coding EMAIL_DOMAIN.
        """
        _, addr = parseaddr(email_address)
        addr = addr or email_address
        if '@' not in addr:
            return None
        domain = addr.rsplit('@', 1)[1].strip().lower().rstrip('.')
        if not domain:
            return None

        ext = _tld_extract(domain)
        registrable = ext.registered_domain
        if not registrable:
            return None

        if ext.subdomain:
            # Subdomain present: key is the label adjacent to the registrable domain.
            # We return the REGISTRABLE parent (not the full host) so the caller can
            # scope the key to its domain — preventing a key registered for one domain
            # from capturing mail arriving on another. See docs/security.md#key-scoping.
            key = ext.subdomain.split('.')[-1]
            return (key, registrable, False)

        # Bare registrable domain: routes to the instance that owns this domain
        return (registrable, registrable, True)

    @staticmethod
    def parse_email_file(file_path: str) -> Optional[Dict[str, Any]]:
        """Parse email file and extract data"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                msg = message_from_file(f)

            # Read raw email content
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                raw_email = f.read()

            # Extract to address
            to_email = msg.get('X-Original-To') or msg.get('To', '')
            if not to_email:
                logger.warning(f"No recipient found in {file_path}")
                return None

            # Resolve recipient to a routing identity (key / verified domain)
            recipient = EmailParserService.parse_recipient(to_email)
            if not recipient:
                logger.warning(f"Could not extract routing key from {to_email}")
                return None
            extracted_key, to_domain, is_bare = recipient

            # Extract from address
            from_header = msg.get('From', '')
            from_name, from_email = parseaddr(from_header)

            # Extract subject
            subject = msg.get('Subject', '')

            # Extract message ID
            message_id = msg.get('Message-ID', '')
            if not message_id:
                # Generate fallback message ID from filename
                message_id = f"<{Path(file_path).name}@{settings.EMAIL_DOMAIN}>"

            # Extract date
            date_header = msg.get('Date')
            try:
                if date_header:
                    received_at = parsedate_to_datetime(date_header)
                    # Convert to UTC and remove timezone info for PostgreSQL
                    if received_at.tzinfo is not None:
                        received_at = received_at.astimezone(timezone.utc).replace(tzinfo=None)
                else:
                    received_at = datetime.utcnow()
            except Exception as e:
                logger.error(f"Error parsing date: {e}")
                received_at = datetime.utcnow()

            # Extract body
            body_text = None
            body_html = None

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == 'text/plain' and not body_text:
                        try:
                            body_text = part.get_payload(decode=True).decode('utf-8', errors='replace')
                        except Exception as e:
                            logger.error(f"Error decoding text/plain: {e}")
                    elif content_type == 'text/html' and not body_html:
                        try:
                            body_html = part.get_payload(decode=True).decode('utf-8', errors='replace')
                        except Exception as e:
                            logger.error(f"Error decoding text/html: {e}")
            else:
                content_type = msg.get_content_type()
                try:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        decoded = payload.decode('utf-8', errors='replace')
                        if content_type == 'text/html':
                            body_html = decoded
                        else:
                            body_text = decoded
                except Exception as e:
                    logger.error(f"Error decoding payload: {e}")

            return {
                'message_id': message_id,
                'from_email': from_email,
                'from_name': from_name if from_name else None,
                'to_email': to_email,
                'subject': subject,
                'body_text': body_text,
                'body_html': body_html,
                'raw_email': raw_email,
                'filename': os.path.basename(file_path),
                'received_at': received_at,
                'extracted_key': extracted_key,
                'to_domain': to_domain,
                'is_bare': is_bare,
            }

        except Exception as e:
            logger.error(f"Error parsing email file {file_path}: {e}")
            return None

    @staticmethod
    async def save_email(session: AsyncSession, email_data: Dict[str, Any]) -> Optional[Email]:
        """Save parsed email to database"""
        try:
            # Check if email already exists
            stmt = select(Email).where(Email.message_id == email_data['message_id'])
            result = await session.execute(stmt)
            existing_email = result.scalar_one_or_none()

            if existing_email:
                logger.info(f"Email {email_data['message_id']} already exists, skipping")
                return existing_email

            # Find the owning instance:
            #  - bare domain  -> a VERIFIED InstanceDomain for that domain
            #  - subdomain    -> an InstanceKey matching the extracted key
            from app.models.instance import Instance
            from app.models.instance_key import InstanceKey
            from app.models.instance_domain import InstanceDomain

            if email_data.get('is_bare'):
                stmt = (
                    select(Instance)
                    .join(InstanceDomain, Instance.id == InstanceDomain.instance_id)
                    .where(
                        InstanceDomain.domain == email_data['to_domain'],
                        InstanceDomain.is_verified.is_(True),
                    )
                )
            else:
                # Subdomain key. Scope it to its parent domain (docs/security.md#key-scoping):
                # the match is valid only when the parent registrable domain is the shared
                # EMAIL_DOMAIN, or a VERIFIED custom domain owned by the SAME instance that
                # holds the key. This stops a key registered under one domain from
                # capturing mail that arrived on a different domain.
                parent_domain = email_data['to_domain']
                stmt = (
                    select(Instance)
                    .join(InstanceKey, Instance.id == InstanceKey.instance_id)
                    .where(InstanceKey.key == email_data['extracted_key'])
                )
                if parent_domain != settings.EMAIL_DOMAIN:
                    # Require a verified InstanceDomain on the same instance.
                    stmt = stmt.join(
                        InstanceDomain, Instance.id == InstanceDomain.instance_id
                    ).where(
                        InstanceDomain.domain == parent_domain,
                        InstanceDomain.is_verified.is_(True),
                    )
            result = await session.execute(stmt)
            instance = result.scalar_one_or_none()

            # Create new email
            email = Email(
                instance_id=instance.id if instance else None,
                extracted_key=email_data['extracted_key'],
                message_id=email_data['message_id'],
                from_email=email_data['from_email'],
                from_name=email_data['from_name'],
                to_email=email_data['to_email'],
                subject=email_data['subject'],
                body_text=email_data['body_text'],
                body_html=email_data['body_html'],
                raw_email=email_data['raw_email'],
                filename=email_data['filename'],
                received_at=email_data['received_at'],
            )

            session.add(email)
            await session.flush()
            logger.info(f"Saved email {email.id} with key {email.extracted_key}")
            return email

        except Exception as e:
            logger.error(f"Error saving email to database: {e}")
            return None

    @staticmethod
    async def process_maildir(session: AsyncSession, maildir_path: str = None) -> int:
        """Process all emails in Maildir"""
        if maildir_path is None:
            maildir_path = settings.MAILDIR_PATH

        if not os.path.exists(maildir_path):
            logger.warning(f"Maildir path {maildir_path} does not exist")
            return 0

        processed_count = 0
        for filename in os.listdir(maildir_path):
            file_path = os.path.join(maildir_path, filename)
            if os.path.isfile(file_path):
                email_data = EmailParserService.parse_email_file(file_path)
                if email_data:
                    email = await EmailParserService.save_email(session, email_data)
                    if email:
                        processed_count += 1

        logger.info(f"Processed {processed_count} emails from {maildir_path}")
        return processed_count
