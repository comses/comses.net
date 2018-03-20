from .test import *

DATABASES['dump_restore'] = {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'dump_restore_{}'.format(config.get('database', 'DB_NAME')),
    'USER': config.get('database', 'DB_USER'),
    'PASSWORD': config.get('database', 'DB_PASSWORD'),
    'HOST': config.get('database', 'DB_HOST'),
    'PORT': config.get('database', 'DB_PORT'),
}


DATABASE_ROUTERS = ['core.database_routers.DumpRestoreRouter', 'core.database_routers.DefaultRouter',]