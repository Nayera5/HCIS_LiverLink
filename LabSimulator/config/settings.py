"""
External Laboratory Simulator: a small, separate Django project with its own SQLite database.
It exchanges HL7 messages with LiverLink and never touches LiverLink's code or database.
For local demos only: there is no login, so everything listens on 127.0.0.1.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'demo-only-not-secret'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

INSTALLED_APPS = ['django.contrib.staticfiles', 'lis']

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
# Own name: cookies ignore the port, so 'csrftoken' would clash with LiverLink's on the same host.
CSRF_COOKIE_NAME = 'lis_csrftoken'

ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'APP_DIRS': True}]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {'timeout': 20, 'transaction_mode': 'IMMEDIATE'},  # HL7 and web threads both write
    }
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

USE_TZ = True
TIME_ZONE = 'UTC'
STATIC_URL = 'static/'

# ---------------------------------------------------------------- HL7 (change with environment variables)
APP_NAME = 'EXTERNAL_LAB'  # our MSH-3: must match the ExternalSystem name in LiverLink
WEB_PORT = int(os.getenv('LIS_WEB_PORT', '8100'))
HL7_HOST = '127.0.0.1'
HL7_PORT = int(os.getenv('LIS_HL7_PORT', '2576'))                  # orders come in here
LIVERLINK_HOST = os.getenv('LIVERLINK_HL7_HOST', '127.0.0.1')
LIVERLINK_PORT = int(os.getenv('LIVERLINK_HL7_PORT', '2575'))      # results go out to here
