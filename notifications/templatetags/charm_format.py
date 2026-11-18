
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter(name="vnd")
def vnd(value):
    """
    Định dạng số tiền Việt Nam.

    1700000.00 -> 1.700.000 đ
    1360000    -> 1.360.000 đ
    None       -> 0 đ

    Chỉ định dạng hiển thị, không thay đổi dữ liệu.
    """
    if value is None or value == "":
        return "0 đ"

    try:
        amount = Decimal(str(value))
        if not amount.is_finite():
            return "0 đ"

        amount = amount.quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )

        formatted = format(amount, ",.0f")
        formatted = formatted.replace(",", ".")

        return f"{formatted} đ"

    except (InvalidOperation, ValueError, TypeError):
        return "0 đ"
