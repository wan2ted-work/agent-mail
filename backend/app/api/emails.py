from aiohttp import web
from sqlalchemy import select, func
from uuid import UUID
import logging

from app.database import db
from app.models.email import Email
from app.models.instance import Instance
from app.api.schemas import EmailResponse, EmailListResponse, ErrorResponse

logger = logging.getLogger(__name__)


async def get_emails_by_secret(request: web.Request) -> web.Response:
    """Get emails by instance secret (UUID) with filtering and search"""
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

        skip = int(request.query.get('skip', 0))
        limit = int(request.query.get('limit', 50))

        # Exact filters
        from_email = request.query.get('from_email', '').strip()
        nickname = request.query.get('nickname', '').strip()
        extracted_key = request.query.get('extracted_key', '').strip()
        subject = request.query.get('subject', '').strip()

        async with db.session() as session:
            # Verify instance exists by secret (ID)
            stmt = select(Instance).where(Instance.id == secret_uuid)
            result = await session.execute(stmt)
            instance = result.scalar_one_or_none()

            if not instance:
                return web.json_response(
                    ErrorResponse(error="Instance not found").model_dump(mode='json'),
                    status=404
                )

            # Build query for emails
            stmt = (
                select(Email)
                .where(Email.instance_id == instance.id)
                .order_by(Email.received_at.desc())
            )

            # Add exact filters if provided
            if from_email:
                stmt = stmt.where(Email.from_email == from_email)
            if nickname:
                # Filter by nickname part of to_email (e.g., "arty.bond" from "arty.bond@myproject.mypm.cloud")
                stmt = stmt.where(Email.to_email.like(f'{nickname}@%'))
            if extracted_key:
                stmt = stmt.where(Email.extracted_key == extracted_key)
            if subject:
                # Partial match for subject
                stmt = stmt.where(Email.subject.like(f'%{subject}%'))

            # Get total count
            count_stmt = select(func.count()).select_from(stmt.alias())
            total_result = await session.execute(count_stmt)
            total = total_result.scalar()

            # Get paginated results
            stmt = stmt.offset(skip).limit(limit)
            result = await session.execute(stmt)
            emails = result.scalars().all()

            response = {
                'total': total,
                'skip': skip,
                'limit': limit,
                'items': [EmailListResponse(
                    id=email.id,
                    from_email=email.from_email,
                    from_name=email.from_name,
                    to_email=email.to_email,
                    extracted_key=email.extracted_key,
                    subject=email.subject,
                    received_at=email.received_at,
                    has_instance=email.instance_id is not None
                ).model_dump(mode='json') for email in emails]
            }

            return web.json_response(response)

    except Exception as e:
        logger.error(f"Error getting emails: {e}")
        return web.json_response(
            ErrorResponse(error="Internal server error", detail=str(e)).model_dump(mode='json'),
            status=500
        )


async def get_email_detail(request: web.Request) -> web.Response:
    """Get email detail by ID"""
    try:
        secret = request.match_info['secret']
        email_id = request.match_info['email_id']

        # Validate UUID format
        try:
            secret_uuid = UUID(secret)
        except ValueError:
            return web.json_response(
                ErrorResponse(error="Invalid secret format (must be UUID)").model_dump(mode='json'),
                status=400
            )

        async with db.session() as session:
            # Verify instance exists by secret
            stmt = select(Instance).where(Instance.id == secret_uuid)
            result = await session.execute(stmt)
            instance = result.scalar_one_or_none()

            if not instance:
                return web.json_response(
                    ErrorResponse(error="Instance not found").model_dump(mode='json'),
                    status=404
                )

            # Get email
            stmt = select(Email).where(
                Email.id == email_id,
                Email.instance_id == instance.id
            )
            result = await session.execute(stmt)
            email = result.scalar_one_or_none()

            if not email:
                return web.json_response(
                    ErrorResponse(error="Email not found").model_dump(mode='json'),
                    status=404
                )

            return web.json_response(
                EmailResponse.from_orm(email).model_dump(mode='json')
            )

    except Exception as e:
        logger.error(f"Error getting email detail: {e}")
        return web.json_response(
            ErrorResponse(error="Internal server error", detail=str(e)).model_dump(mode='json'),
            status=500
        )




async def get_orphaned_emails(request: web.Request) -> web.Response:
    """Get emails without instance (orphaned)"""
    try:
        skip = int(request.query.get('skip', 0))
        limit = int(request.query.get('limit', 50))

        # Exact filters
        from_email = request.query.get('from_email', '').strip()
        nickname = request.query.get('nickname', '').strip()
        extracted_key = request.query.get('extracted_key', '').strip()
        subject = request.query.get('subject', '').strip()

        async with db.session() as session:
            # Get orphaned emails
            stmt = (
                select(Email)
                .where(Email.instance_id.is_(None))
                .order_by(Email.received_at.desc())
            )

            # Add exact filters if provided
            if from_email:
                stmt = stmt.where(Email.from_email == from_email)
            if nickname:
                stmt = stmt.where(Email.to_email.like(f'{nickname}@%'))
            if extracted_key:
                stmt = stmt.where(Email.extracted_key == extracted_key)
            if subject:
                # Partial match for subject
                stmt = stmt.where(Email.subject.like(f'%{subject}%'))

            # Get total count
            count_stmt = select(func.count()).select_from(stmt.alias())
            total_result = await session.execute(count_stmt)
            total = total_result.scalar()

            # Get paginated results
            stmt = stmt.offset(skip).limit(limit)
            result = await session.execute(stmt)
            emails = result.scalars().all()

            response = {
                'total': total,
                'skip': skip,
                'limit': limit,
                'items': [EmailListResponse(
                    id=email.id,
                    from_email=email.from_email,
                    from_name=email.from_name,
                    to_email=email.to_email,
                    extracted_key=email.extracted_key,
                    subject=email.subject,
                    received_at=email.received_at,
                    has_instance=False
                ).model_dump(mode='json') for email in emails]
            }

            return web.json_response(response)

    except Exception as e:
        logger.error(f"Error getting orphaned emails: {e}")
        return web.json_response(
            ErrorResponse(error="Internal server error", detail=str(e)).model_dump(mode='json'),
            status=500
        )
