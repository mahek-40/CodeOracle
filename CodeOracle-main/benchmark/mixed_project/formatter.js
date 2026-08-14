/**
 * String and payload formatting utilities.
 */
export function formatPayload(data) {
  if (!data || typeof data !== 'object') {
    return JSON.stringify({ error: 'Invalid data' });
  }
  return JSON.stringify({
    timestamp: Date.now(),
    payload: data,
  });
}

export function sanitizeInput(str) {
  if (typeof str !== 'string') return '';
  return str.trim().replace(/[<>]/g, '');
}
