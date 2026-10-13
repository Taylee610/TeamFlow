from .settings import *

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
SECRET_KEY = 'test-only-secret-key-at-least-thirty-two-characters'
LOGGING = {'version': 1, 'disable_existing_loggers': False, 'loggers': {'django.request': {'level': 'CRITICAL'}}}
REST_FRAMEWORK = {**REST_FRAMEWORK, 'DEFAULT_THROTTLE_CLASSES': []}
