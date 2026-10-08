from pathlib import Path
import os
from django.core.management.utils import get_random_secret_key
BASE_DIR = Path(__file__).resolve().parent.parent
# A unique local key is generated once and excluded from the ZIP and Git.
key_file = BASE_DIR / '.secret_key'
if not os.environ.get('DJANGO_SECRET_KEY') and not key_file.exists():
    key_file.write_text(get_random_secret_key())
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or key_file.read_text().strip()
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]').split(',')
INSTALLED_APPS = ['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','booking']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3','OPTIONS':{'timeout':20}}}
if os.environ.get('DB_ENGINE') == 'mysql':
    DATABASES = {'default': {'ENGINE':'django.db.backends.mysql','NAME':os.environ.get('DB_NAME','movie_booking'),'USER':os.environ.get('DB_USER','root'),'PASSWORD':os.environ.get('DB_PASSWORD',''),'HOST':os.environ.get('DB_HOST','127.0.0.1'),'PORT':os.environ.get('DB_PORT','3306'),'OPTIONS':{'charset':'utf8mb4'}}}
AUTH_PASSWORD_VALIDATORS = [{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator'},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR/'static']
STATIC_ROOT = BASE_DIR/'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR/'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DATA_UPLOAD_MAX_MEMORY_SIZE = 4 * 1024 * 1024
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_FAILURE_VIEW = 'booking.views.csrf_failure'
