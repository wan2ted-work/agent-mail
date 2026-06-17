from aiohttp import web
from sqlalchemy import select, func
import logging

from app.database import db
from app.models.email import Email
from app.models.instance import Instance
from app.api.helpers import api_handler, serialize, ApiError
from app.api.schemas import EmailResponse, EmailListResponse

logger = logging.getLogger(__name__)

_MAX_LIMIT = 200


def _int_param(request: web.Request, name: str, default: int) -> int:
    raw = request.query.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise ApiError(f"Query param '{name}' must be an integer", 400)


def _like_escape(value: str) -> str:
    """Escape LIKE/ILIKE wildcards so user input matches literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _apply_filters(stmt, request: web.Request):
    """Apply the shared from_email / nickname / extracted_key / subject filters."""
    from_email = request.query.get("from_email", "").strip()
    nickname = request.query.get("nickname", "").strip()
    extracted_key = request.query.get("extracted_key", "").strip()
    subject = request.query.get("subject", "").strip()

    if from_email:
        stmt = stmt.where(Email.from_email == from_email)
    if nickname:
        stmt = stmt.where(Email.to_email.ilike(f"{_like_escape(nickname)}@%", escape="\\"))
    if extracted_key:
        stmt = stmt.where(Email.extracted_key == extracted_key)
    if subject:
        stmt = stmt.where(Email.subject.ilike(f"%{_like_escape(subject)}%", escape="\\"))
    return stmt


async def _paginated_list(request: web.Request, session, base_stmt) -> dict:
    """Run a filtered, paginated email-list query and return the response dict."""
    skip = max(_int_param(request, "skip", 0), 0)
    limit = min(max(_int_param(request, "limit", 50), 1), _MAX_LIMIT)

    stmt = _apply_filters(base_stmt.order_by(Email.received_at.desc()), request)

    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar()
    emails = (await session.execute(stmt.offset(skip).limit(limit))).scalars().all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            EmailListResponse(
                id=e.id,
                from_email=e.from_email,
                from_name=e.from_name,
                to_email=e.to_email,
                extracted_key=e.extracted_key,
                subject=e.subject,
                received_at=e.received_at,
                has_instance=e.instance_id is not None,
            ).model_dump(mode="json")
            for e in emails
        ],
    }


@api_handler()
async def get_emails_by_secret(request: web.Request) -> web.Response:
    """List an instance's emails, newest first, with optional filters."""
    secret_uuid = request["secret_uuid"]

    async with db.session() as session:
        instance = (
            await session.execute(select(Instance).where(Instance.id == secret_uuid))
        ).scalar_one_or_none()
        if not instance:
            raise ApiError("Instance not found", 404)

        base = select(Email).where(Email.instance_id == instance.id)
        return web.json_response(await _paginated_list(request, session, base))


@api_handler()
async def get_email_detail(request: web.Request) -> web.Response:
    """Get one email by id, scoped to the owning instance."""
    secret_uuid = request["secret_uuid"]
    email_id = request.match_info["email_id"]

    async with db.session() as session:
        instance = (
            await session.execute(select(Instance).where(Instance.id == secret_uuid))
        ).scalar_one_or_none()
        if not instance:
            raise ApiError("Instance not found", 404)

        email = (
            await session.execute(
                select(Email).where(Email.id == email_id, Email.instance_id == instance.id)
            )
        ).scalar_one_or_none()
        if not email:
            raise ApiError("Email not found", 404)

        return web.json_response(serialize(EmailResponse, email))


@api_handler(require_secret=False)
async def get_orphaned_emails(request: web.Request) -> web.Response:
    """List emails not yet routed to any instance (operator/debug; admin-gated)."""
    async with db.session() as session:
        base = select(Email).where(Email.instance_id.is_(None))
        return web.json_response(await _paginated_list(request, session, base))
