#!/usr/bin/env python3
"""Record storage-preflight ordering without inspecting host storage."""

import json
import os
from pathlib import Path


with Path(os.environ["FAKE_DOCKER_LOG"]).open("a", encoding="utf-8") as stream:
    stream.write(json.dumps({"event": "preflight"}) + "\n")
