from django.core.exceptions import ObjectDoesNotExist, ValidationError


def register_error_handlers(api):
    @api.exception_handler(ObjectDoesNotExist)
    def not_found(request, exc):
        return api.create_response(request, {'detail': 'Nie znaleziono.'}, status=404)

    @api.exception_handler(ValidationError)
    def invalid(request, exc):
        msg = '; '.join(exc.messages) if hasattr(exc, 'messages') else str(exc)
        return api.create_response(request, {'detail': msg}, status=400)
