from django.utils.deprecation import MiddlewareMixin
from django.contrib.messages import get_messages
import logging

logger = logging.getLogger(__name__)

class AjaxMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.is_ajax = lambda: request.headers.get('X-Requested-With') == 'XMLHttpRequest'


class NoDebugMessagesMiddleware(MiddlewareMixin):
    excluded_paths = ('/messages/',)  # Tuple of strings

    def process_request(self, request):
        path = request.path
        full_path = request.get_full_path()
        logger.debug(f"Processing request path: {path} with full path: {full_path}")
        if any(path.startswith(excluded_path) for excluded_path in self.excluded_paths):
            logger.debug("Clearing messages for path: " + full_path)
            storage = get_messages(request)
            list(storage)  # Consume all messages to clear them
            storage.used = True

