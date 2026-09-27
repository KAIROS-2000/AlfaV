from __future__ import annotations

from collections.abc import Mapping


DEFAULT_PAGE_SIZE = 15
MAX_PAGE_SIZE = 15


def _bounded_positive_int(value, default: int, *, maximum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    parsed = max(parsed, 1)
    return min(parsed, maximum) if maximum is not None else parsed


def pagination_params(
    args: Mapping,
    *,
    page_key: str = 'page',
    page_size_key: str = 'page_size',
) -> tuple[int, int]:
    return (
        _bounded_positive_int(args.get(page_key), 1),
        _bounded_positive_int(args.get(page_size_key), DEFAULT_PAGE_SIZE, maximum=MAX_PAGE_SIZE),
    )


def pagination_payload(total: int, page: int, page_size: int) -> dict:
    return {
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': max(1, (total + page_size - 1) // page_size),
    }


def paginate_query(query, *, page: int, page_size: int):
    total = query.order_by(None).count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return rows, pagination_payload(total, page, page_size)
