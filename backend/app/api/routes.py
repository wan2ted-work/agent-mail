from aiohttp import web
from app.api import instances, emails


def setup_routes(app: web.Application):
    """Setup all API routes"""

    # Instance routes
    app.router.add_get('/api/instances/{secret}', instances.get_instance)
    app.router.add_put('/api/instances/{secret}', instances.update_instance)
    app.router.add_delete('/api/instances/{secret}', instances.delete_instance)

    # Instance Key routes
    app.router.add_get('/api/instances/{secret}/keys', instances.get_instance_keys)
    app.router.add_post('/api/instances/{secret}/keys', instances.add_instance_key)
    app.router.add_delete('/api/instances/{secret}/keys/{key}', instances.remove_instance_key)

    # Instance Domain routes (custom domains with DNS TXT verification)
    app.router.add_get('/api/instances/{secret}/domains', instances.get_instance_domains)
    app.router.add_post('/api/instances/{secret}/domains', instances.add_instance_domain)
    app.router.add_post('/api/instances/{secret}/domains/{domain}/verify', instances.verify_instance_domain)
    app.router.add_delete('/api/instances/{secret}/domains/{domain}', instances.remove_instance_domain)

    # Email routes (using secret for access)
    app.router.add_get('/api/instances/{secret}/emails', emails.get_emails_by_secret)
    app.router.add_get('/api/instances/{secret}/emails/{email_id}', emails.get_email_detail)
    app.router.add_get('/api/emails/orphaned', emails.get_orphaned_emails)

    # Health check
    app.router.add_get('/health', health_check)


async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint"""
    return web.json_response({'status': 'ok'})
