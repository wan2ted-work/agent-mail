/**
 * Decode RFC 2047 encoded email headers
 * Format: =?charset?encoding?encoded-text?=
 * Example: =?UTF-8?B?0JDQu9C10LrRgdCw0L3QtNGAINCV0LLRgdC40L0=?=
 */
export function decodeEmailHeader(header) {
  if (!header) return '';

  // Check if header is encoded
  const encodedPattern = /=\?([^?]+)\?([BQ])\?([^?]+)\?=/gi;

  if (!encodedPattern.test(header)) {
    return header;
  }

  // Reset regex lastIndex
  encodedPattern.lastIndex = 0;

  return header.replace(encodedPattern, (match, charset, encoding, encodedText) => {
    try {
      if (encoding.toUpperCase() === 'B') {
        // Base64 decoding
        const decoded = atob(encodedText);
        // Decode UTF-8
        return decodeURIComponent(escape(decoded));
      } else if (encoding.toUpperCase() === 'Q') {
        // Quoted-printable decoding
        const decoded = encodedText
          .replace(/_/g, ' ')
          .replace(/=([0-9A-F]{2})/g, (_, hex) =>
            String.fromCharCode(parseInt(hex, 16))
          );
        return decodeURIComponent(escape(decoded));
      }
    } catch (error) {
      console.error('Error decoding header:', error);
      return match;
    }

    return match;
  });
}

/**
 * Decode email name/subject
 */
export function decodeEmailName(name) {
  if (!name) return '';
  return decodeEmailHeader(name);
}
