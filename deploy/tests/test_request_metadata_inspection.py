"""Local regression test for the allowlisted metadata inspection script."""

import io
import json
import runpy
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4


class MetadataInspectionTests(unittest.TestCase):
    def test_inspection_script_includes_timestamp_and_excludes_sensitive_fields(self):
        edge_id = str(uuid4())
        timestamp = "2021-01-01T00:00:00.123+00:00"
        records = [
            {
                "layer": layer,
                "timestamp": timestamp,
                "request_id": edge_id,
                "request_id_source": "incoming",
                "event": "request_finished",
                "status": 200,
                "url": "/secret?token=secret",
                "cookie": "secret",
                "message": "secret",
            }
            for layer in ("nginx", "django")
        ]
        script = Path(__file__).resolve().parents[1] / "scripts/check-request-metadata"
        with (
            patch("sys.argv", [str(script), edge_id]),
            patch(
                "builtins.open",
                side_effect=[io.StringIO(json.dumps(record)) for record in records],
            ),
            patch("sys.stdout", io.StringIO()) as output,
        ):
            runpy.run_path(str(script), run_name="__main__")
        inspected = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(len(inspected), 2)
        self.assertEqual([record["timestamp"] for record in inspected], [timestamp] * 2)
        self.assertNotIn("secret", output.getvalue())


if __name__ == "__main__":
    unittest.main()
