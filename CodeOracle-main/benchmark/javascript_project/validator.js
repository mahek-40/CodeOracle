/**
 * Benchmark JavaScript Project — Validator Module
 */

export function validateItem(item) {
  if (!item || typeof item !== 'object') {
    return 'Item must be an object';
  }
  if (!item.id || typeof item.id !== 'string') {
    return 'Item ID is required and must be a string';
  }
  if (typeof item.price !== 'number' || item.price < 0 || isNaN(item.price)) {
    return 'Item price must be a non-negative number';
  }
  if (item.quantity !== undefined && (typeof item.quantity !== 'number' || item.quantity <= 0)) {
    return 'Item quantity must be a positive integer';
  }
  return null;
}

export function validateEmail(email) {
  if (!email || typeof email !== 'string') {
    return false;
  }
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email.trim());
}

export function sanitizeString(input) {
  if (typeof input !== 'string') {
    return '';
  }
  return input.replace(/[<>]/g, '').trim();
}
