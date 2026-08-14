"""
Benchmark Python Project — Order Processor Module
Contains order lifecycle methods, status validation, and billing calculations.
"""
from typing import List, Dict, Optional
from discount_rules import calculate_tier_discount, apply_promotional_code
from tax_calculator import compute_sales_tax


class OrderItem:
    def __init__(self, item_id: str, name: str, price: float, quantity: int = 1):
        if price < 0:
            raise ValueError("Price cannot be negative")
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero")
        self.item_id = item_id
        self.name = name
        self.price = price
        self.quantity = quantity

    def subtotal(self) -> float:
        return round(self.price * self.quantity, 2)


class OrderProcessor:
    """Processes customer orders, applies discounts, taxes, and manages status."""

    def __init__(self, customer_id: str, state_code: str = "CA"):
        self.customer_id = customer_id
        self.state_code = state_code
        self.items: List[OrderItem] = []
        self.status = "draft"  # draft, pending, approved, cancelled
        self.applied_discount = 0.0

    def add_item(self, item: OrderItem) -> None:
        if self.status != "draft":
            raise RuntimeError("Cannot add items to non-draft order")
        self.items.append(item)

    def calculate_subtotal(self) -> float:
        return sum(item.subtotal() for item in self.items)

    def apply_coupon(self, coupon_code: str, total_orders_count: int = 0) -> float:
        subtotal = self.calculate_subtotal()
        tier_discount = calculate_tier_discount(subtotal, total_orders_count)
        promo_discount = apply_promotional_code(coupon_code, subtotal)
        self.applied_discount = max(tier_discount, promo_discount)
        return self.applied_discount

    def calculate_total(self, is_tax_exempt: bool = False) -> Dict[str, float]:
        subtotal = self.calculate_subtotal()
        discounted_subtotal = max(0.0, subtotal - self.applied_discount)
        tax = compute_sales_tax(discounted_subtotal, self.state_code, is_tax_exempt)
        total = round(discounted_subtotal + tax, 2)

        return {
            "subtotal": subtotal,
            "discount": self.applied_discount,
            "taxable_amount": discounted_subtotal,
            "tax": tax,
            "grand_total": total,
        }

    def approve_order(self) -> bool:
        if not self.items:
            raise ValueError("Cannot approve an empty order")
        if self.status != "draft":
            return False
        self.status = "approved"
        return True

    def cancel_order(self, reason: str = "") -> bool:
        if self.status == "cancelled":
            return False
        self.status = "cancelled"
        return True
