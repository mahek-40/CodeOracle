/**
 * Benchmark JavaScript Project — Formatter Module
 */

export function formatCurrency(amount, currency = 'USD') {
  if (typeof amount !== 'number' || isNaN(amount)) {
    return '$0.00';
  }
  const formatted = amount.toFixed(2);
  if (currency === 'EUR') {
    return `€${formatted}`;
  } else if (currency === 'GBP') {
    return `£${formatted}`;
  }
  return `$${formatted}`;
}

export function formatPercentage(rate) {
  if (typeof rate !== 'number' || isNaN(rate)) {
    return '0%';
  }
  return `${Math.round(rate * 100)}%`;
}

export function formatItemReceipt(item) {
  if (!item) return '';
  const subtotal = (item.price || 0) * (item.quantity || 1);
  return `${item.name || 'Item'} x${item.quantity || 1}: ${formatCurrency(subtotal)}`;
}
