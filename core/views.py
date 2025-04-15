from django.shortcuts import redirect
from django.utils import translation
from django.conf import settings

def set_language(request):
    """Set the user's language preference"""
    lang_code = request.POST.get('language', settings.LANGUAGE_CODE)
    
    # Set the language
    translation.activate(lang_code)
    
    # Save to session
    request.session[translation.LANGUAGE_SESSION_KEY] = lang_code
    
    # Redirect back to the same page
    response = redirect(request.META.get('HTTP_REFERER', '/'))
    
    # Set cookie
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang_code)
    
    return response