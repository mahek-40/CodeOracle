"""
Benchmark Python Project — Discount Rules Module
Contains volume pricing, coupon verification, and VIP rewards.
"""

def calculate_tier_discount(subtotal: float, order_count: int) -> float:
    """Calculates customer loyalty volume discount."""
    if subtotal <= 0:
        return 0.0

    discount_rate = 0.0
    if order_count >= 50:
        discount_rate = 0.20
    elif order_count >= 20:
        discount_rate = 0.15
    elif order_count >= 5:
        discount_rate = 0.10
    elif subtotal >= 500.0:
        discount_rate = 0.08
    elif subtotal >= 100.0:
        discount_rate = 0.05

    return round(subtotal * discount_rate, 2)


def apply_promotional_code(code: str, subtotal: float) -> float:
    """Verifies promotional code strings and returns discount amount."""
    if not code or subtotal <= 0:
        return 0.0

    clean_code = code.strip().upper()

    if clean_code == "SAVE50":
        return min(50.0, subtotal)
    elif clean_code == "VIP25":
        return round(subtotal * 0.25, 2)
    elif clean_code == "FREESHIP":
        return 10.0
    elif clean_code == "WELCOME10":
        return round(subtotal * 0.10, 2)
    else:
        return 0.0


def is_vip_customer(total_spend: float, tenure_months: int) -> bool:
    """Determines whether customer qualifies for VIP status."""
    if total_spend >= 2500.0 and tenure_months >= 12:
        return True
    if total_spend >= 5000.0:
        return True
    return False
