#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")

    from django.core.management import execute_from_command_line

    print("django settings module: ", os.environ.get("DJANGO_SETTINGS_MODULE"))
    execute_from_command_line(sys.argv)
