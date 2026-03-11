from flask import request


def paginate(query, page=1, per_page=20, max_per_page=100):
    per_page = min(per_page, max_per_page)
    page = max(1, page)

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        "items": paginated.items,
        "pagination": {
            "page": paginated.page,
            "per_page": paginated.per_page,
            "total_pages": paginated.pages,
            "total_items": paginated.total,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev,
            "next_page": paginated.next_num if paginated.has_next else None,
            "prev_page": paginated.prev_num if paginated.has_prev else None,
        },
    }


def get_pagination_params():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    return max(1, page), min(max(1, per_page), 100)
