from django.utils.deprecation import MiddlewareMixin

class AjaxMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.is_ajax = lambda: request.headers.get('X-Requested-With') == 'XMLHttpRequest'
