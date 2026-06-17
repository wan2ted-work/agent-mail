/**
 * Decode RFC 2047 encoded email headers.
 * Format: =?charset?encoding?encoded-text?=
 * Example: =?UTF-8?B?0JDQu9C10LrRgdCw0L3QtNGAINCV0LLRgdC40L0=?=
 */
export function decodeEmailHeader(header) {
  if (!header) return '';

  // Non-global regex so .replace below isn't affected by a stateful lastIndex.
  const encodedPattern = /=\?([^?]+)\?([BQ])\?([^?]+)\?=/gi;

  return header.replace(encodedPattern, (match, charset, encoding, encodedText) => {
    try {
      let bytes;
      if (encoding.toUpperCase() === 'B') {
        // Base64 -> raw bytes
        const binary = atob(encodedText);
        bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
      } else {
        // Quoted-printable: "_" is space, "=XX" is a hex byte.
        const qp = encodedText.replace(/_/g, ' ');
        const out = [];
        for (let i = 0; i < qp.length; i += 1) {
          if (qp[i] === '=' && i + 2 < qp.length) {
            out.push(parseInt(qp.substr(i + 1, 2), 16));
            i += 2;
          } else {
            out.push(qp.charCodeAt(i));
          }
        }
        bytes = Uint8Array.from(out);
      }
      // Charset-correct decoding (handles UTF-8 and most legacy charsets).
      return new TextDecoder(charset || 'utf-8').decode(bytes);
    } catch (err) {
      console.error('Error decoding header:', err);
      return match;
    }
  });
}
