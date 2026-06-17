from aiohttp import web
from sqlalchemy import select, func
import logging

from app.database import db
from app.services.instance_service import InstanceService
from app.models.instance import Instance
from app.models.email import Email
from app.api.helpers import api_handler, json_error, serialize, ApiError
from app.api.schemas import (
    InstanceUpdate,
    InstanceResponse,
    InstanceKeyCreate,
    InstanceKeyResponse,
    InstanceDomainCreate,
    InstanceDomainResponse,
    MessageResponse,
)
from app.config import settings

logger = logging.getLogger(__name__)


def _domain_payload(d) -> dict:
    """Serialize an InstanceDomain plus the DNS (MX) record the user must create."""
    payload = serialize(InstanceDomainResponse, d)
    payload['dns_record'] = {
        'type': 'MX',
        'name': d.domain,
        'value': settings.MAIL_HOST,
        'priority': 10,
        'hint': f"Point {d.domain}'s MX to {settings.MAIL_HOST}, then verify.",
    }
    return payload


@api_handler()
async def get_instance(request: web.Request) -> web.Response:
    """Get instance by secret (UUID) — creates a new instance if not found."""
    secret_uuid = request["secret_uuid"]

    async with db.session() as session:
        instance = await InstanceService.get_instance_by_id(session, secret_uuid)

        if not instance:
            # Auto-create on first access.
            created = await InstanceService.create_instance(
                session, secret=secret_uuid, description=None
            )
            if not created:
                raise ApiError("Failed to create instance", 500)
            # Reload with keys eagerly loaded to avoid a lazy-load during
            # serialization (would raise MissingGreenlet in async context).
            instance = await InstanceService.get_instance_by_id(session, secret_uuid)
            return web.json_response({**serialize(InstanceResponse, instance), 'email_count': 0})

        stmt = select(func.count(Email.id)).where(Email.instance_id == instance.id)
        result = await session.execute(stmt)
        email_count = result.scalar()

        return web.json_response({**serialize(InstanceResponse, instance), 'email_count': email_count})


@api_handler()
async def update_instance(request: web.Request) -> web.Response:
    """Update an instance's description / active flag."""
    secret_uuid = request["secret_uuid"]
    update_data = InstanceUpdate(**await request.json())

    async with db.session() as session:
        instance = await InstanceService.get_instance_by_id(session, secret_uuid)
        if not instance:
            raise ApiError("Instance not found", 404)

        updated = await InstanceService.update_instance(
            session,
            instance.id,
            description=update_data.description,
            is_active=update_data.is_active,
        )
        return web.json_response(serialize(InstanceResponse, updated))


@api_handler()
async def delete_instance(request: web.Request) -> web.Response:
    """Delete an instance (its emails become orphaned)."""
    secret_uuid = request["secret_uuid"]

    async with db.session() as session:
        instance = await InstanceService.get_instance_by_id(session, secret_uuid)
        if not instance:
            raise ApiError("Instance not found", 404)

        if not await InstanceService.delete_instance(session, instance.id):
            raise ApiError("Failed to delete instance", 500)

        return web.json_response(MessageResponse(message="Instance deleted successfully").model_dump(mode='json'))


@api_handler()
async def add_instance_key(request: web.Request) -> web.Response:
    """Add a key to an instance (back-associates matching orphaned mail)."""
    secret_uuid = request["secret_uuid"]
    key_data = InstanceKeyCreate(**await request.json())

    async with db.session() as session:
        instance_key = await InstanceService.add_key(session, instance_id=secret_uuid, key=key_data.key)
        if not instance_key:
            raise ApiError("Failed to add key (instance not found or key already exists)", 400)
        return web.json_response(serialize(InstanceKeyResponse, instance_key), status=201)


@api_handler()
async def remove_instance_key(request: web.Request) -> web.Response:
    """Remove a key from an instance."""
    secret_uuid = request["secret_uuid"]
    key = request.match_info['key']

    async with db.session() as session:
        if not await InstanceService.remove_key(session, instance_id=secret_uuid, key=key):
            raise ApiError("Key not found for this instance", 404)
        return web.json_response(MessageResponse(message=f"Key '{key}' removed successfully").model_dump(mode='json'))


@api_handler()
async def get_instance_keys(request: web.Request) -> web.Response:
    """List all keys for an instance."""
    secret_uuid = request["secret_uuid"]

    async with db.session() as session:
        instance = await InstanceService.get_instance_by_id(session, secret_uuid)
        if not instance:
            raise ApiError("Instance not found", 404)

        keys = await InstanceService.get_keys(session, secret_uuid)
        return web.json_response([serialize(InstanceKeyResponse, key) for key in keys])


# ----------------------------------------------------------------------
# Custom domains (verified by MX record)
# ----------------------------------------------------------------------

@api_handler()
async def get_instance_domains(request: web.Request) -> web.Response:
    """List all custom domains for an instance."""
    secret_uuid = request["secret_uuid"]

    async with db.session() as session:
        instance = await InstanceService.get_instance_by_id(session, secret_uuid)
        if not instance:
            raise ApiError("Instance not found", 404)

        domains = await InstanceService.get_domains(session, secret_uuid)
        return web.json_response([_domain_payload(d) for d in domains])


@api_handler()
async def add_instance_domain(request: web.Request) -> web.Response:
    """Register a custom domain (returns the MX record to create)."""
    secret_uuid = request["secret_uuid"]
    domain_data = InstanceDomainCreate(**await request.json())

    async with db.session() as session:
        instance_domain = await InstanceService.add_domain(session, instance_id=secret_uuid, domain=domain_data.domain)
        if not instance_domain:
            raise ApiError("Failed to add domain (instance not found, invalid, or domain already registered)", 400)
        return web.json_response(_domain_payload(instance_domain), status=201)


@api_handler()
async def verify_instance_domain(request: web.Request) -> web.Response:
    """Check the domain's MX record and mark it verified if it points to MAIL_HOST."""
    secret_uuid = request["secret_uuid"]
    domain = request.match_info['domain']

    async with db.session() as session:
        instance_domain = await InstanceService.verify_domain(session, secret_uuid, domain)
        if not instance_domain:
            raise ApiError("Domain not found for this instance", 404)

        payload = _domain_payload(instance_domain)
        status = 200 if instance_domain.is_verified else 202
        if not instance_domain.is_verified:
            payload['message'] = (
                f"MX record not pointing to {settings.MAIL_HOST} yet. Add the MX "
                f"record and retry (DNS propagation can take a few minutes)."
            )
        return web.json_response(payload, status=status)


@api_handler()
async def remove_instance_domain(request: web.Request) -> web.Response:
    """Remove a custom domain from an instance."""
    secret_uuid = request["secret_uuid"]
    domain = request.match_info['domain']

    async with db.session() as session:
        if not await InstanceService.remove_domain(session, secret_uuid, domain):
            raise ApiError("Domain not found for this instance", 404)
        return web.json_response(MessageResponse(message=f"Domain '{domain}' removed successfully").model_dump(mode='json'))
