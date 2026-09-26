"""Content-addressed local objects, atomically published without replacement."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

from thermoscope.firms import IngestError


class ObjectStore:
    def __init__(self, root: Path):
        self.root = root

    def put_once(self, relative: str, payload: bytes):
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
                temp_path = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temp_path, target)
            except FileExistsError:
                if target.read_bytes() != payload:
                    raise IngestError("OBJECT_HASH_CONFLICT") from None
        finally:
            if temp_path:
                temp_path.unlink(missing_ok=True)

    def save_raw(self, payload: bytes, suffix: str = "csv") -> str:
        content_hash = hashlib.sha256(payload).hexdigest()
        self.put_once(f"raw/{content_hash}.{suffix}", payload)
        return content_hash

    def save_manifest(self, run_id: str, manifest: dict):
        self.put_once(
            f"manifests/{run_id}.json",
            (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
        )
