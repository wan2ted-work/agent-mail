import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.instance import Instance
from app.models.email import Email
from app.models.instance_key import InstanceKey
from app.models.instance_domain import InstanceDomain

logger = logging.getLogger(__name__)

# A custom domain is verified when its MX record points to our mail host
# (settings.MAIL_HOST) — i.e. mail for that domain actually reaches this server.
# That is both the proof of ownership and the functional requirement.


class InstanceService:
    """Service for managing instances"""

    @staticmethod
    async def create_instance(
        session: AsyncSession,
        secret: Optional[UUID] = None,
        description: Optional[str] = None
    ) -> Optional[Instance]:
        """
        Create new instance without keys (keys are added separately)
        """
        try:
            # Generate secret if not provided
            instance_id = secret if secret else uuid4()

            # Check if secret (id) already exists
            stmt = select(Instance).where(Instance.id == instance_id)
            result = await session.execute(stmt)
            existing_by_id = result.scalar_one_or_none()

            if existing_by_id:
                logger.warning(f"Instance with secret {instance_id} already exists")
                return None

            # Create new instance with provided or generated secret as ID
            instance = Instance(
                id=instance_id,
                description=description,
                is_active=True
            )
            session.add(instance)
            await session.flush()

            logger.info(f"Created instance {instance.id}")

            return instance

        except Exception as e:
            logger.error(f"Error creating instance: {e}")
            raise

    @staticmethod
    async def get_instance_by_key(session: AsyncSession, key: str) -> Optional[Instance]:
        """Get instance by key (searches through InstanceKey table) with keys loaded"""
        stmt = (
            select(Instance)
            .options(selectinload(Instance.keys), selectinload(Instance.domains))
            .join(InstanceKey, Instance.id == InstanceKey.instance_id)
            .where(InstanceKey.key == key)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_instance_by_id(session: AsyncSession, instance_id: UUID) -> Optional[Instance]:
        """Get instance by ID with keys loaded"""
        stmt = (
            select(Instance)
            .options(selectinload(Instance.keys), selectinload(Instance.domains))
            .where(Instance.id == instance_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_instances(
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[Instance]:
        """List all instances with keys loaded"""
        stmt = (
            select(Instance)
            .options(selectinload(Instance.keys), selectinload(Instance.domains))
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_instance(
        session: AsyncSession,
        instance_id: UUID,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Instance]:
        """Update instance"""
        instance = await InstanceService.get_instance_by_id(session, instance_id)
        if not instance:
            return None

        if description is not None:
            instance.description = description
        if is_active is not None:
            instance.is_active = is_active

        await session.flush()
        return instance

    @staticmethod
    async def delete_instance(session: AsyncSession, instance_id: UUID) -> bool:
        """Delete instance (emails will have instance_id set to NULL)"""
        instance = await InstanceService.get_instance_by_id(session, instance_id)
        if not instance:
            return False

        await session.delete(instance)
        await session.flush()
        logger.info(f"Deleted instance {instance_id}")
        return True

    @staticmethod
    async def add_key(session: AsyncSession, instance_id: UUID, key: str) -> Optional[InstanceKey]:
        """Add a key to an instance and associate orphaned emails"""
        try:
            # Check if instance exists
            instance = await InstanceService.get_instance_by_id(session, instance_id)
            if not instance:
                logger.warning(f"Instance {instance_id} not found")
                return None

            # Check if key already exists
            stmt = select(InstanceKey).where(InstanceKey.key == key)
            result = await session.execute(stmt)
            existing_key = result.scalar_one_or_none()

            if existing_key:
                logger.warning(f"Key '{key}' already exists")
                return None

            # Create new instance key
            instance_key = InstanceKey(
                instance_id=instance_id,
                key=key
            )
            session.add(instance_key)
            await session.flush()

            # Associate orphaned emails for this key — but only those that arrived on
            # the SHARED EMAIL_DOMAIN. Orphans on a custom domain are intentionally
            # left for domain verification to claim, so a key can't back-capture mail
            # from a domain the instance hasn't proven it owns
            # (docs/security.md#key-scoping). We match on the recipient host suffix.
            shared_suffix = f".{settings.EMAIL_DOMAIN}"
            stmt = (
                update(Email)
                .where(
                    Email.extracted_key == key,
                    Email.instance_id.is_(None),
                    Email.to_email.ilike(f"%@%{shared_suffix}"),
                )
                .values(instance_id=instance_id)
            )
            result = await session.execute(stmt)
            associated_count = result.rowcount

            logger.info(
                f"Added key '{key}' to instance {instance_id} "
                f"and associated {associated_count} orphaned emails"
            )

            return instance_key

        except Exception as e:
            logger.error(f"Error adding key to instance: {e}")
            raise

    @staticmethod
    async def remove_key(session: AsyncSession, instance_id: UUID, key: str) -> bool:
        """Remove a key from an instance"""
        try:
            # Find the key
            stmt = select(InstanceKey).where(
                InstanceKey.instance_id == instance_id,
                InstanceKey.key == key
            )
            result = await session.execute(stmt)
            instance_key = result.scalar_one_or_none()

            if not instance_key:
                logger.warning(f"Key '{key}' not found for instance {instance_id}")
                return False

            # Delete the key
            await session.delete(instance_key)
            await session.flush()

            logger.info(f"Removed key '{key}' from instance {instance_id}")
            return True

        except Exception as e:
            logger.error(f"Error removing key from instance: {e}")
            raise

    @staticmethod
    async def get_keys(session: AsyncSession, instance_id: UUID) -> List[InstanceKey]:
        """Get all keys for an instance"""
        stmt = (
            select(InstanceKey)
            .where(InstanceKey.instance_id == instance_id)
            .order_by(InstanceKey.created_at)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Custom domains
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_domain(domain: str) -> str:
        return (domain or "").strip().lower().rstrip('.')

    @staticmethod
    async def get_domains(session: AsyncSession, instance_id: UUID) -> List[InstanceDomain]:
        """Get all custom domains for an instance"""
        stmt = (
            select(InstanceDomain)
            .where(InstanceDomain.instance_id == instance_id)
            .order_by(InstanceDomain.created_at)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def add_domain(session: AsyncSession, instance_id: UUID, domain: str) -> Optional[InstanceDomain]:
        """Register a custom domain (unverified) for an instance"""
        try:
            domain = InstanceService._normalize_domain(domain)
            if not domain or '.' not in domain:
                logger.warning(f"Invalid domain '{domain}'")
                return None

            instance = await InstanceService.get_instance_by_id(session, instance_id)
            if not instance:
                logger.warning(f"Instance {instance_id} not found")
                return None

            # Domain must be globally unique (it routes mail to exactly one instance)
            stmt = select(InstanceDomain).where(InstanceDomain.domain == domain)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                logger.warning(f"Domain '{domain}' already registered")
                return None

            instance_domain = InstanceDomain(
                instance_id=instance_id,
                domain=domain,
                is_verified=False,
            )
            session.add(instance_domain)
            await session.flush()
            logger.info(f"Registered domain '{domain}' for instance {instance_id} (unverified)")
            return instance_domain

        except Exception as e:
            logger.error(f"Error adding domain to instance: {e}")
            raise

    @staticmethod
    async def _dns_query(name: str, rtype: str) -> List[dict]:
        """Resolve DNS records via DNS-over-HTTPS (Google). Returns the Answer list."""
        try:
            async with aiohttp.ClientSession() as http:
                async with http.get(
                    "https://dns.google/resolve",
                    params={"name": name, "type": rtype},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json(content_type=None)
            return data.get("Answer", []) or []
        except Exception as e:
            logger.error(f"DNS {rtype} lookup failed for {name}: {e}")
            return []

    @staticmethod
    async def _mx_points_here(domain: str) -> bool:
        """True if the domain's MX points to our mail host (mail reaches us)."""
        mail_host = settings.MAIL_HOST.lower().rstrip('.')
        mx = await InstanceService._dns_query(domain, "MX")  # type 15
        hosts = []
        for a in mx:
            # data looks like "10 mail.mypm.cloud."
            parts = a.get("data", "").split()
            if parts:
                hosts.append(parts[-1].lower().rstrip('.'))
        if mail_host in hosts:
            return True
        # Fallback: any MX host (or the bare domain) that resolves to our IP
        for host in hosts or [domain]:
            for a in await InstanceService._dns_query(host, "A"):  # type 1
                if a.get("data") == settings.MAIL_SERVER_IP:
                    return True
        return False

    @staticmethod
    async def verify_domain(session: AsyncSession, instance_id: UUID, domain: str) -> Optional[InstanceDomain]:
        """Verify a custom domain by checking its MX points to our mail host."""
        domain = InstanceService._normalize_domain(domain)
        stmt = select(InstanceDomain).where(
            InstanceDomain.instance_id == instance_id,
            InstanceDomain.domain == domain,
        )
        result = await session.execute(stmt)
        instance_domain = result.scalar_one_or_none()
        if not instance_domain:
            return None

        if instance_domain.is_verified:
            return instance_domain

        if not await InstanceService._mx_points_here(domain):
            logger.info(f"Verification failed for '{domain}': MX does not point to {settings.MAIL_HOST}")
            return instance_domain  # still unverified; caller checks is_verified

        instance_domain.is_verified = True
        instance_domain.verified_at = datetime.utcnow()

        # Attach any bare-domain emails that arrived before verification
        assoc = (
            update(Email)
            .where(Email.extracted_key == domain, Email.instance_id.is_(None))
            .values(instance_id=instance_id)
        )
        res = await session.execute(assoc)
        await session.flush()
        logger.info(f"Verified domain '{domain}' for instance {instance_id}; linked {res.rowcount} orphaned emails")
        return instance_domain

    @staticmethod
    async def remove_domain(session: AsyncSession, instance_id: UUID, domain: str) -> bool:
        """Remove a custom domain from an instance"""
        try:
            domain = InstanceService._normalize_domain(domain)
            stmt = select(InstanceDomain).where(
                InstanceDomain.instance_id == instance_id,
                InstanceDomain.domain == domain,
            )
            result = await session.execute(stmt)
            instance_domain = result.scalar_one_or_none()
            if not instance_domain:
                return False

            await session.delete(instance_domain)
            await session.flush()
            logger.info(f"Removed domain '{domain}' from instance {instance_id}")
            return True

        except Exception as e:
            logger.error(f"Error removing domain from instance: {e}")
            raise
