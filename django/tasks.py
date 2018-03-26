import os
import sys

# push current directory onto the path to access core.settings
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")

from curator.invoke_tasks import ns