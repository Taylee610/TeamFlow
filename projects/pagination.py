from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Default page size of 10, but lets clients ask for more (e.g. the
    React dashboard requesting ?page_size=200 to compute aggregates)."""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 200