import asyncio
import logging
from aiohttp import web
import aiohttp_cors

from app.config import settings
from app.database import db
from app.api.routes import setup_routes
from app.workers import email_monitor
from app.security import admin_token_middleware, rate_limit_middleware_factory

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def init_app() -> web.Application:
    """Initialize the application"""
    app = web.Application(middlewares=[
        rate_limit_middleware_factory(),
        admin_token_middleware,
    ])

    # Setup CORS from config. With explicit origins we can safely allow credentials;
    # with the "*" wildcard we must NOT (browsers reject credentialed wildcard CORS).
    origins = settings.cors_origins
    wildcard = origins == ["*"] or not origins
    resource_options = aiohttp_cors.ResourceOptions(
        allow_credentials=not wildcard,
        expose_headers="*",
        allow_headers="*",
        allow_methods="*",
    )
    defaults = {"*": resource_options} if wildcard else {o: resource_options for o in origins}
    cors = aiohttp_cors.setup(app, defaults=defaults)

    # Setup routes
    setup_routes(app)

    # Configure CORS on all routes
    for route in list(app.router.routes()):
        cors.add(route)

    # Setup startup and cleanup
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    return app


async def on_startup(app: web.Application):
    """Startup handler"""
    logger.info("Starting Email Reader API...")

    # Initialize database
    try:
        await db.init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Start email monitor worker
    app['email_monitor_task'] = asyncio.create_task(email_monitor.start())
    logger.info("Email monitor worker started")

    logger.info(f"Server started on {settings.HOST}:{settings.PORT}")


async def on_cleanup(app: web.Application):
    """Cleanup handler"""
    logger.info("Shutting down Email Reader API...")

    # Stop email monitor worker
    if 'email_monitor_task' in app:
        await email_monitor.stop()
        app['email_monitor_task'].cancel()
        try:
            await app['email_monitor_task']
        except asyncio.CancelledError:
            pass
        logger.info("Email monitor worker stopped")

    # Close database connection
    await db.close()
    logger.info("Database connection closed")


def main():
    """Main entry point"""
    app = asyncio.run(init_app())
    web.run_app(app, host=settings.HOST, port=settings.PORT)


if __name__ == '__main__':
    main()
