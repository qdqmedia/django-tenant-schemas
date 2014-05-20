from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import get_apps, get_models
if "south" in settings.INSTALLED_APPS:
    from south.management.commands.syncdb import Command as SyncdbCommand
else:
    from django.core.management.commands.syncdb import Command as SyncdbCommand
from django.db import connection
from tenant_schemas.utils import get_tenant_model, get_public_schema_name
from tenant_schemas.management.commands import SyncCommon


class Command(SyncCommon):
    help = "Sync schemas based on TENANT_APPS and SHARED_APPS settings"
    option_list = SyncdbCommand.option_list + SyncCommon.option_list

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        if "south" in settings.INSTALLED_APPS:
            self.options["migrate"] = False

        for app, model in self._iter_model_apps():
            # save original settings
            setattr(model._meta, 'was_managed', model._meta.managed)
            # Set model info to know if the models should be individually shared
            setattr(model._meta, 'shared_model',
                    ('.'.join((app.__name__, model.__name__)) in
                     getattr(settings, 'SHARED_MODELS', ())))

        ContentType.objects.clear_cache()

        if self.sync_public:
            self.sync_public_apps()
        if self.sync_tenant:
            self.sync_tenant_apps(self.schema_name)

        # restore settings
        for model in get_models(include_auto_created=True):
            model._meta.managed = model._meta.was_managed

    def _iter_model_apps(self, include_auto_created=True):
        """Iters for each (app, model)"""
        for app_model in get_apps():
            for model in get_models(app_model, include_auto_created=True):
                yield (app_model, model)

    def _set_managed_apps(self, included_apps, tenant=True):
        """ sets which apps are managed by syncdb """
        for model in get_models(include_auto_created=True):
            model._meta.managed = False

        verbosity = int(self.options.get('verbosity'))
        for app, model in self._iter_model_apps():
            app_name = app.__name__.replace('.models', '')
            if (app_name in included_apps and
                    not (tenant and model._meta.shared_model)):
                model._meta.managed = model._meta.was_managed
                if model._meta.managed and verbosity >= 3:
                    self._notice("=== Include Model: %s: %s" % (app_name, model.__name__))

    def _sync_tenant(self, tenant):
        self._notice("=== Running syncdb for schema: %s" % tenant.schema_name)
        connection.set_tenant(tenant, include_public=False)
        SyncdbCommand().execute(**self.options)
        for model in get_models():
            if model._meta.shared_model:
                cursor = connection.cursor()
                cursor.execute(
                    'CREATE VIEW {schema}.{table} AS SELECT * FROM public.{table}'.format(
                        schema=tenant.schema_name, table=model._meta.db_table))

    def sync_tenant_apps(self, schema_name=None):
        apps = self.tenant_apps or self.installed_apps
        self._set_managed_apps(apps)
        if schema_name:
            tenant = get_tenant_model().objects.filter(schema_name=schema_name).get()
            self._sync_tenant(tenant)
        else:
            all_tenants = get_tenant_model().objects.exclude(schema_name=get_public_schema_name())
            if not all_tenants:
                self._notice("No tenants found!")

            for tenant in all_tenants:
                self._sync_tenant(tenant)

    def sync_public_apps(self):
        apps = self.shared_apps or self.installed_apps
        self._set_managed_apps(apps, tenant=False)
        SyncdbCommand().execute(**self.options)
        self._notice("=== Running syncdb for schema public")
