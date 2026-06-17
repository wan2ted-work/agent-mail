from aiohttp import web
from sqlalchemy import select, func
import logging
from uuid import UUID

from app.database import db
from app.services.instance_service import InstanceService
from app.models.instance import Instance
from app.models.email import Email
from app.api.schemas import (
    InstanceUpdate,
    InstanceResponse,
    InstanceWithEmailCount,
    InstanceKeyCreate,
    InstanceKeyResponse,
    InstanceDomainCreate,
    InstanceDomainResponse,
    MessageResponse,
    ErrorResponse
)
from app.config import settings

logger = logging.getLogger(__name__)


def _domain_payload(d) -> dict:
    """Serialize an InstanceDomain plus the DNS record the user must create."""
    payload = InstanceDomainResponse.from_orm(d).model_dump(mode='json')
    payload['dns_record'] = {
        'type': 'MX',
        'name': d.domain,
        'value': settings.MAIL_HOST,
        'priority': 10,
        'hint': f"Point {d.domain}'s MX to {settings.MAIL_HOST}, then verify.",
    }
    return payload


# async def list_instances(request: web.Request) -> web.Response:
#     """List all instances with email counts"""
#     try:
#         skip = int(request.query.get('skip', 0))
#         limit = int(request.query.get('limit', 100))
#
#         async with db.session() as session:
#             # Get instances with email counts
#             stmt = (
#                 select(
#                     Instance,
#                     func.count(Email.id).label('email_count')
#                 )
#                 .outerjoin(Email, Instance.id == Email.instance_id)
#                 .group_by(Instance.id)
#                 .offset(skip)
#                 .limit(limit)
#             )
#
#             result = await session.execute(stmt)
#             rows = result.all()
#
#             instances = [
#                 {
#                     **InstanceResponse.from_orm(row[0]).model_dump(mode='json'),
#                     'email_count': row[1]
#                 }
#                 for row in rows
#             ]
#
#             return web.json_response(instances)
#
#     except Exception as e:
#         logger.error(f"Error listing instances: {e}")
#         return web.json_response(
#             ErrorResponse(error="Internal server error", detail=str(e)).model_dump(mode='json'),
#             status=500
#         )


async def get_instance(request: web.Request) -> web.Response:
    """Get instance by secret (UUID) - creates new instance if not found"""
    try:
        secret = request.match_info['secret']

        # Validate UUID format
        try:
            secret_uuid = UUID(secret)
        except ValueError:
            return web.json_response(
                ErrorResponse(error="Invalid secret format (must be UUID)").model_dump(mode='json'),
                status=400
            )

        async with db.session() as session:
            instance = await InstanceService.get_instance_by_id(session, secret_uuid)

            # If instance not found, create it automatically
            if not instance:
                instance = await InstanceService.create_instance(
                    session,
                    secret=secret_uuid,
                    description=None
                )

                if not instance:
                    # Should not happen unless there's a race condition
                    return web.json_response(
                        ErrorResponse(error="Failed to create instance").model_dump(mode='json'),
                        status=500
                    )

                # Reload with keys eagerly loaded to avoid a lazy-load during
                # serialization (would raise MissingGreenlet in async context)
                instance = await InstanceService.get_instance_by_id(session, secret_uuid)

                # Return new instance with zero emails
                response = {
                    **InstanceResponse.from_orm(instance).model_dump(mode='json'),
                    'email_count': 0
                }
                return web.json_response(response)

            # Get email count for existing instance
            stmt = select(func.count(Email.id)).where(Email.instance_id == instance.id)
            result = await session.execute(stmt)
            email_count = result.scalar()

            response = {
                **InstanceResponse.from_orm(instance).model_dump(mode='json'),
                'email_count': email_count
            }

            return web.json_response(response)

    except Exception as e:
        logger.error(f"Error getting instance: {e}")
        return web.json_response(
            ErrorResponse(error="Internal server error", detail=str(e)).model_dump(mode='json'),
            status=500
        )


async def update_instance(request: web.Request) -> web.Response:
    """Update instance"""
    try:
        secret = request.match_info['secret']

        # Validate UUID format
        try:
            secret_uuid = UUID(secret)
        except ValueError:
            return web.json_response(
                ErrorResponse(error="Invalid secret format (must be UUID)").model_dump(mode='json'),
                status=400
            )

        data = await request.json()
        update_data = InstanceUpdate(**data)

        async with db.session() as session:
            # Get instance by secret (ID)
            instance = await InstanceService.get_instance_by_id(session, secret_uuid)
            if not instance:
                return web.json_response(
                    ErrorResponse(error="Instance not found").model_dump(mode='json'),
                    status=404
                )

            # Update instance
            updated = await InstanceService.update_instance(
                session,
                instance.id,
                description=update_data.description,
                is_active=update_data.is_active
            )

            return web.json_response(
                InstanceResponse.from_orm(updated).model_dump(mode='json')
            )

    except ValueError as e:
        return web.json_response(
            ErrorResponse(error="Validation error", detail=str(e)).model_dump(mode='json'),
            status=400
        )
    except Exception as e:
        logger.error(f"Error updating instance: {e}")
        return web.json_response(
            ErrorResponse(error="Internal server error", detail=str(e)).model_dump(mode='json'),
            status=500
        )


async def delete_instance(request: web.Request) -> web.Response:
    """Delete instance"""
    try:
        secret = request.match_info['secret']

        # Validate UUID format
        try:
            secret_uuid = UUID(secret)
        except ValueError:
            return web.json_response(
                ErrorResponse(error="Invalid secret format (must be UUID)").model_dump(mode='json'),
                status=400
            )

        async with db.session() as session:
            # Get instance by secret (ID)
            instance = await InstanceService.get_instance_by_id(session, secret_uuid)
            if not instance:
                return web.json_response(
                    ErrorResponse(error="Instance not found").model_dump(mode='json'),
                    status=404
                )

            # Delete instance
            success = await InstanceService.delete_instance(session, instance.id)

            if success:
                return web.json_response(
                    MessageResponse(message=f"Instance deleted successfully").model_dump(mode='json')
                )
            else:
                return web.json_response(
                    ErrorResponse(error="Failed to delete instance").model_dump(mode='json'),
                    status=500
                )

    except Exception as e:
        logger.error(f"Error deleting instance: {e}")
        return web.json_response(
            ErrorResponse(error="Internal server error", detail=str(e)).model_dump(mode='json'),
            status=500
        )


async def add_instance_key(request: web.Request) -> web.Response:
    """Add a key to an instance"""
    try:
        secret = request.match_info['secret']

        # Validate UUID format
        try:
            secret_uuid = UUID(secret)
        except ValueError:
            return web.json_response(
                ErrorResponse(error="Invalid secret format (must be UUID)").model_dump(mode='json'),
                status=400
            )

        data = await request.json()
        key_data = InstanceKeyCreate(**data)

        async with db.session() as session:
            # Add key to instance
            instance_key = await InstanceService.add_key(
                session,
                instance_id=secret_uuid,
                key=key_data.key
            )

            if not instance_key:
                return web.json_response(
                    ErrorResponse(error="Failed to add key (instance not found or key already exists)").model_dump(mode='json'),
                    status=400
                )

            return web.json_response(
                InstanceKeyResponse.from_orm(instance_key).model_dump(mode='json'),
                status=201
            )

    except ValueError as e:
        return web.json_response(
            ErrorResponse(error="Validation error", detail=str(e)).model_dump(mode='json'),
            status=400
        )
    except Exception as e:
        logger.error(f"Error adding instance key: {e}")
        return web.json_response(
            ErrorResponse(error="Internal server error", detail=str(e)).model_dump(mode='json'),
            status=500
        )


async def remove_instance_key(request: web.Request) -> web.Response:
    """Remove a key from an instance"""
    try:
        secret = request.match_info['secret']
        key = request.match_info['key']

        # Validate UUID format
        try:
            secret_uuid = UUID(secret)
        except ValueError:
            return web.json_response(
                ErrorResponse(error="Invalid secret format (must be UUID)").model_dump(mode='json'),
                status=400
            )

        async with db.session() as session:
            # Remove key from instance
            success = await InstanceService.remove_key(
                session,
                instance_id=secret_uuid,
                key=key
            )

            if not success:
                return web.json_response(
                    ErrorResponse(error="Key not found for this instance").model_dump(mode='json'),
                    status=404
                )

            return web.json_response(
                MessageResponse(message=f"Key '{key}' removed successfully").model_dump(mode='json')
            )

    except Exception as e:
        logger.error(f"Error removing instance key: {e}")
        return web.json_response(
            ErrorResponse(error="Internal server error", detail=str(e)).model_dump(mode='json'),
            status=500
        )


async def get_instance_keys(request: web.Request) -> web.Response:
    """Get all keys for an instance"""
    try:
        secret = request.match_info['secret']

        # Validate UUID format
        try:
            secret_uuid = UUID(secret)
        except ValueError:
            return web.json_response(
                ErrorResponse(error="Invalid secret format (must be UUID)").model_dump(mode='json'),
                status=400
            )

        async with db.session() as session:
            # Verify instance exists
            instance = await InstanceService.get_instance_by_id(session, secret_uuid)
            if not instance:
                return web.json_response(
                    ErrorResponse(error="Instance not found").model_dump(mode='json'),
                    status=404
                )

            # Get all keys
            keys = await InstanceService.get_keys(session, secret_uuid)

            response = [
                InstanceKeyResponse.from_orm(key).model_dump(mode='json')
                for key in keys
            ]

            return web.json_response(response)

    except Exception as e:
        logger.error(f"Error getting instance keys: {e}")
        return web.json_response(
            ErrorResponse(error="Internal server error", detail=str(e)).model_dump(mode='json'),
            status=500
        )


# ----------------------------------------------------------------------
# Custom domains
# ----------------------------------------------------------------------

def _parse_secret(request):
    """Return (secret_uuid, error_response). error_response is None on success."""
    try:
        return UUID(request.match_info['secret']), None
    except ValueError:
        return None, web.json_response(
            ErrorResponse(error="Invalid secret format (must be UUID)").model_dump(mode='json'),
            status=400
        )


async def get_instance_domains(request: web.Request) -> web.Response:
    """Get all custom domains for an instance"""
    try:
        secret_uuid, err = _parse_secret(request)
        if err:
            return err

        async with db.session() as session:
            instance = await InstanceService.get_instance_by_id(session, secret_uuid)
            if not instance:
                return web.json_response(
                    ErrorResponse(error="Instance not found").model_dump(mode='json'),
                    status=404
                )

            domains = await InstanceService.get_domains(session, secret_uuid)
            return web.json_response([_domain_payload(d) for d in domains])

    except Exception as e:
        logger.error(f"Error getting instance domains: {e}")
        return web.json_response(
            ErrorResponse(error="Internal server error", detail=str(e)).model_dump(mode='json'),
            status=500
        )


async def add_instance_domain(request: web.Request) -> web.Response:
    """Register a custom domain (returns the TXT record to create)"""
    try:
        secret_uuid, err = _parse_secret(request)
        if err:
            return err

        data = await request.json()
        domain_data = InstanceDomainCreate(**data)

        async with db.session() as session:
            instance_domain = await InstanceService.add_domain(
                session, instance_id=secret_uuid, domain=domain_data.domain
            )
            if not instance_domain:
                return web.json_response(
                    ErrorResponse(error="Failed to add domain (instance not found, invalid, or domain already registered)").model_dump(mode='json'),
                    status=400
                )

            return web.json_response(_domain_payload(instance_domain), status=201)

    except ValueError as e:
        return web.json_response(
            ErrorResponse(error="Validation error", detail=str(e)).model_dump(mode='json'),
            status=400
        )
    except Exception as e:
        logger.error(f"Error adding instance domain: {e}")
        return web.json_response(
            ErrorResponse(error="Internal server error", detail=str(e)).model_dump(mode='json'),
            status=500
        )


async def verify_instance_domain(request: web.Request) -> web.Response:
    """Check the DNS TXT record and mark the domain verified if present"""
    try:
        secret_uuid, err = _parse_secret(request)
        if err:
            return err
        domain = request.match_info['domain']

        async with db.session() as session:
            instance_domain = await InstanceService.verify_domain(session, secret_uuid, domain)
            if not instance_domain:
                return web.json_response(
                    ErrorResponse(error="Domain not found for this instance").model_dump(mode='json'),
                    status=404
                )

            payload = _domain_payload(instance_domain)
            status = 200 if instance_domain.is_verified else 202
            if not instance_domain.is_verified:
                payload['message'] = f"MX record not pointing to {settings.MAIL_HOST} yet. Add the MX record and retry (DNS propagation can take a few minutes)."
            return web.json_response(payload, status=status)

    except Exception as e:
        logger.error(f"Error verifying instance domain: {e}")
        return web.json_response(
            ErrorResponse(error="Internal server error", detail=str(e)).model_dump(mode='json'),
            status=500
        )


async def remove_instance_domain(request: web.Request) -> web.Response:
    """Remove a custom domain from an instance"""
    try:
        secret_uuid, err = _parse_secret(request)
        if err:
            return err
        domain = request.match_info['domain']

        async with db.session() as session:
            success = await InstanceService.remove_domain(session, secret_uuid, domain)
            if not success:
                return web.json_response(
                    ErrorResponse(error="Domain not found for this instance").model_dump(mode='json'),
                    status=404
                )

            return web.json_response(
                MessageResponse(message=f"Domain '{domain}' removed successfully").model_dump(mode='json')
            )

    except Exception as e:
        logger.error(f"Error removing instance domain: {e}")
        return web.json_response(
            ErrorResponse(error="Internal server error", detail=str(e)).model_dump(mode='json'),
            status=500
        )
