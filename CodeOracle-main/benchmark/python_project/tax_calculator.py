"""
Benchmark Python Project — Tax Calculator Module
Computes jurisdiction-specific sales taxes and tax exemptions.
"""

STATE_TAX_RATES = {
    "CA": 0.0825,
    "NY": 0.0800,
    "TX": 0.0625,
    "FL": 0.0600,
    "WA": 0.0650,
    "OR": 0.0000,
    "DE": 0.0000,
    "NH": 0.0000,
    "MT": 0.0000,
}

DEFAULT_TAX_RATE = 0.0500


def get_state_rate(state_code: str) -> float:
    """Returns statutory base tax rate for given state code."""
    clean_state = state_code.strip().upper() if state_code else ""
    return STATE_TAX_RATES.get(clean_state, DEFAULT_TAX_RATE)


def compute_sales_tax(
    amount: float,
    state_code: str,
    is_tax_exempt: bool = False,
) -> float:
    """Calculates total sales tax with exemption checks."""
    if amount <= 0 or is_tax_exempt:
        return 0.0

    rate = get_state_rate(state_code)
    return round(amount * rate, 2)


def is_tax_free_state(state_code: str) -> bool:
    """Returns True if the state has 0% sales tax."""
    return get_state_rate(state_code) == 0.0
