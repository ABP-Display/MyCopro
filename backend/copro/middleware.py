class PrivateResponses:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.contrib.auth import logout
        from django.http import JsonResponse
        from .models import MFA
        response=None
        if request.path.startswith('/api/') and request.user.is_authenticated:
            item=MFA.objects.filter(user=request.user,enabled_at__isnull=False).first()
            if item and request.session.get('mfa_generation')!=str(item.generation):
                logout(request)
                response=JsonResponse({'error':'Reconnectez-vous avec votre code A2F pour poursuivre.','login_required':True},status=401)
        if response is None:response = self.get_response(request)
        if request.path.startswith('/api/'):
            response['Cache-Control'] = 'private, no-store'
            response['X-Content-Type-Options'] = 'nosniff'
        return response
