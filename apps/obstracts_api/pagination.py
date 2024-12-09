from rest_framework.pagination import PageNumberPagination, InvalidPage
from rest_framework.exceptions import NotFound

class CustomPagination(PageNumberPagination):
    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate a queryset if required, either returning a
        page object, or `None` if pagination is not configured for this view.
        """
        self.request = request
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = self.django_paginator_class(queryset, page_size)
        page_number = self.get_page_number(request, paginator)

        try:
            self.page = paginator.page(page_number)
        except InvalidPage as exc:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Invalid page request: {exc}")
            raise NotFound("Invalid page number.")

        if paginator.num_pages > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True

        return self.page