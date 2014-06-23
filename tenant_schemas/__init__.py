from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from tenant_schemas.utils import get_public_schema_name, get_tenant_model


recommended_config = """
Warning: You should put 'tenant_schemas' at the end of INSTALLED_APPS like this:
INSTALLED_APPS = TENANT_APPS + SHARED_APPS + ('tenant_schemas',)
This is neccesary to overwrite built-in django management commands with their schema-aware implementations.
"""
# Make a bunch of tests for configuration recommendations
# These are best practices basically, to avoid hard to find bugs, unexpected behaviour
if not hasattr(settings, 'TENANT_APPS'):
    print ImproperlyConfigured('TENANT_APPS setting not set')

if not settings.TENANT_APPS:
    raise ImproperlyConfigured("TENANT_APPS is empty. Maybe you don't need this app?")

if settings.INSTALLED_APPS[-1] != 'tenant_schemas':
    print recommended_config

