/**
 * Benchmark JavaScript Project — Cart Manager Module
 */
import { validateItem, validateEmail } from './validator.js';
import { formatCurrency } from './formatter.js';

export class CartManager {
  constructor(customerEmail) {
    if (customerEmail && !validateEmail(customerEmail)) {
      throw new Error('Invalid customer email address');
    }
    this.customerEmail = customerEmail;
    this.items = [];
    this.couponDiscount = 0;
  }

  addItem(item) {
    const error = validateItem(item);
    if (error) {
      throw new Error(`Invalid item: ${error}`);
    }
    const existing = this.items.find(i => i.id === item.id);
    if (existing) {
      existing.quantity += item.quantity || 1;
    } else {
      this.items.push({ ...item, quantity: item.quantity || 1 });
    }
  }

  removeItem(itemId) {
    const initialLen = this.items.length;
    this.items = this.items.filter(i => i.id !== itemId);
    return this.items.length < initialLen;
  }

  getSubtotal() {
    return this.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  }

  applyCoupon(code) {
    const cleanCode = (code || '').trim().toUpperCase();
    if (cleanCode === 'SAVE20') {
      this.couponDiscount = 0.20;
    } else if (cleanCode === 'HALF') {
      this.couponDiscount = 0.50;
    } else {
      this.couponDiscount = 0;
    }
    return this.couponDiscount;
  }

  getTotal() {
    const subtotal = this.getSubtotal();
    const discount = subtotal * this.couponDiscount;
    return Math.max(0, subtotal - discount);
  }

  checkout() {
    if (this.items.length === 0) {
      throw new Error('Cannot checkout an empty cart');
    }
    const total = this.getTotal();
    return {
      status: 'confirmed',
      totalFormatted: formatCurrency(total),
      itemCount: this.items.length,
    };
  }
}
