from .production import *

MAINTENANCE_MODE = True

INSTALLED_APPS = ['maintenance_mode'] + INSTALLED_APPS

MIDDLEWARE += 'maintenance_mode.middleware.MaintenanceModeMiddleware'
