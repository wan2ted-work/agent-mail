// Runtime configuration, sourced from Vite env vars (baked in at build time).
// These let the UI work for any deployment. Override them via .env / build args:
// VITE_API_URL, VITE_EMAIL_DOMAIN, VITE_MAIL_HOST, VITE_APP_NAME, VITE_APP_TAGLINE.

// Product branding (override per deployment if you fork/rebrand).
export const APP_NAME = import.meta.env.VITE_APP_NAME || 'Agent Mail';
export const APP_TAGLINE = import.meta.env.VITE_APP_TAGLINE || 'Disposable inboxes on the fly';

// Base URL of the Agent Mail backend API.
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

// Base domain used to display subdomain-key addresses: anything@<key>.<EMAIL_DOMAIN>
export const EMAIL_DOMAIN = import.meta.env.VITE_EMAIL_DOMAIN || 'example.com';

// Host that custom domains must point their MX record to (shown in the verify UI).
export const MAIL_HOST = import.meta.env.VITE_MAIL_HOST || `mail.${EMAIL_DOMAIN}`;

// Build a full subdomain-key email address for display/copy.
export function keyAddress(key, localpart = 'anything') {
  return `${localpart}@${key}.${EMAIL_DOMAIN}`;
}
