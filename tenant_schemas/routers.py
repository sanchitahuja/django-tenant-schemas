from django.conf import settings
from django.db.models.base import ModelBase
from django.db.utils import load_backend

from tenant_schemas.utils import SchemaRouter


class TenantSyncRouter(object):
    """
    A router to control which applications will be synced,
    depending if we are syncing the shared apps or the tenant apps.
    """

    def db_for_read(self, model, **hints):
        from django.db import connection
        return SchemaRouter.get_db_based_on_model(model=model, schema_name=connection.schema_name)

    def db_for_write(self, model, **hints):
        from django.db import connection
        return SchemaRouter.get_db_based_on_model(model=model, schema_name=connection.schema_name)

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # the imports below need to be done here else django <1.5 goes crazy
        # https://code.djangoproject.com/ticket/20704
        from django.db import connection
        from tenant_schemas.utils import get_public_schema_name, app_labels
        from tenant_schemas.postgresql_backend.base import DatabaseWrapper as TenantDbWrapper

        db_engine = settings.DATABASES[db]['ENGINE']
        if not (db_engine == 'tenant_schemas.postgresql_backend' or
                issubclass(getattr(load_backend(db_engine), 'DatabaseWrapper'), TenantDbWrapper)):
            return None

        if isinstance(app_label, ModelBase):
            # In django <1.7 the `app_label` parameter is actually `model`
            app_label = app_label._meta.app_label

        app_output = True
        if connection.schema_name == get_public_schema_name():
            if app_label not in app_labels(settings.SHARED_APPS):
                return False
        else:
            if app_label not in app_labels(settings.TENANT_APPS):
                return False

        # print("allow_migrate",  db, app_label, model_name, hints, "MYOUTPUT",
        #       SchemaRouter.get_db_based_on_model(connection.schema_name))
        return app_output and db == SchemaRouter.get_db_based_on_model(connection.schema_name)

    def allow_syncdb(self, db, model):
        # allow_syncdb was changed to allow_migrate in django 1.7
        return self.allow_migrate(db, model)
