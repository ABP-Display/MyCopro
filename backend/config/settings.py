import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
COPRO_PUBLIC_URL = os.environ.get('COPRO_PUBLIC_URL','').rstrip('/')
DEBUG = False
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver,copro.ydoxide.fr').split(',')
CSRF_TRUSTED_ORIGINS = [v for v in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if v]
INSTALLED_APPS = ['django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','copro']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware',
              'django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware',
              'django.contrib.auth.middleware.AuthenticationMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware',
              'copro.middleware.PrivateResponses']
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
if os.environ.get('POSTGRES_HOST'):
    DATABASES = {'default': {'ENGINE':'django.db.backends.postgresql','HOST':os.environ['POSTGRES_HOST'],
        'NAME':os.environ.get('POSTGRES_DB','copro_simple'),'USER':'copro','PASSWORD':os.environ['POSTGRES_PASSWORD']}}
else:
    DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3'}}
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
MEDIA_ROOT = Path(os.environ.get('COPRO_MEDIA_ROOT', BASE_DIR/'media'))
SESSION_COOKIE_NAME = 'copro_simple_session'
CSRF_COOKIE_NAME = 'copro_simple_csrf'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 28800
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = os.environ.get('HTTPS_ONLY') == '1'
CSRF_FAILURE_VIEW = 'copro.views.csrf_failure'
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
AUTH_PASSWORD_VALIDATORS = [
    {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':12}},
    {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
]
