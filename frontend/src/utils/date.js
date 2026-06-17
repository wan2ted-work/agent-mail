// Date formatting helpers. All guard against invalid input so the UI never renders
// the literal string "Invalid Date".

function parse(value) {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

// Short date, e.g. "Jun 17, 2026".
export function formatDate(value) {
  const d = parse(value);
  if (!d) return '—';
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

// Full date + time, e.g. "June 17, 2026, 02:30:00 PM".
export function formatDateTime(value) {
  const d = parse(value);
  if (!d) return '—';
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

// Relative time, e.g. "5 minutes ago" / "in 2 days"; falls back to a short date.
export function formatRelative(value) {
  const d = parse(value);
  if (!d) return '—';
  const diffMs = d.getTime() - Date.now();
  const abs = Math.abs(diffMs);
  const units = [
    ['day', 86400000],
    ['hour', 3600000],
    ['minute', 60000],
    ['second', 1000],
  ];
  if (abs >= 7 * 86400000) return formatDate(value);
  const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
  for (const [unit, ms] of units) {
    if (abs >= ms || unit === 'second') {
      return rtf.format(Math.round(diffMs / ms), unit);
    }
  }
  return formatDate(value);
}
