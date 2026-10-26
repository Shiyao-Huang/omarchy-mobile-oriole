#!/usr/bin/env python3
"""Stage a checksummed experiment; does not select Mesa or change system libraries."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile


def stage(archive, expected, destination):
    archive, destination = Path(archive), Path(destination)
    if re.fullmatch(r'[0-9a-f]{64}', expected) is None:
        raise ValueError('invalid SHA256')
    # Work on the same open archive throughout validation and extraction.
    with archive.open('rb') as source:
        digest = hashlib.sha256()
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
        if digest.hexdigest() != expected:
            raise ValueError('archive digest mismatch')
        source.seek(0)
        if destination.exists() or destination.is_symlink():
            raise FileExistsError('preserve existing candidate/manual edits')
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix='.mesa-stage-', dir=destination.parent)).resolve()
        try:
            with tarfile.open(fileobj=source, mode='r:*') as tf:
                members = tf.getmembers()
                names, links = set(), set()
                if sum(m.size for m in members) > 512 * 1024 * 1024:
                    raise ValueError('expanded archive exceeds bound')
                for m in members:
                    p = PurePosixPath(m.name)
                    if p.is_absolute() or '..' in p.parts or not p.parts:
                        raise ValueError('invalid archive path')
                    if str(p) in names:
                        raise ValueError('duplicate archive path')
                    names.add(str(p))
                    if not (m.isdir() or m.isfile() or m.issym()):
                        raise ValueError('special file or hardlink forbidden')
                    if m.issym():
                        target = PurePosixPath(m.linkname)
                        # Mesa SONAME links are simple sibling-relative filenames.
                        if target.is_absolute() or '..' in target.parts or not target.parts:
                            raise ValueError('escaping link')
                        links.add(str(p))
                for m in members:
                    if any(str(p) in links for p in PurePosixPath(m.name).parents):
                        raise ValueError('archive writes through a symlink')
                # Extract regular files first; no tar ownership, devices or special modes.
                for m in members:
                    p = temporary / m.name
                    if m.isdir():
                        p.mkdir(parents=True, exist_ok=True)
                    elif m.isfile():
                        p.parent.mkdir(parents=True, exist_ok=True)
                        with p.open('xb') as out, tf.extractfile(m) as inp:
                            shutil.copyfileobj(inp, out)
                        p.chmod(0o755 if m.mode & 0o111 else 0o644)
                for m in members:
                    if m.issym():
                        p = temporary / m.name
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.symlink_to(m.linkname)
                for link in links:
                    p = temporary / link
                    resolved = p.resolve(strict=True)
                    if temporary not in resolved.parents:
                        raise ValueError('resolved link escapes staging')
            if not (temporary / 'lib').is_dir():
                raise ValueError('missing private library directory')
            record = temporary / 'oriole-stage.json'
            if record.exists() or record.is_symlink():
                raise ValueError('reserved manifest name')
            record.write_text(json.dumps({'archive_sha256': expected, 'selected': False}) + '\n')
            # mkdtemp is private while staging; published libraries must be readable
            # by the compositor's unprivileged user, including every directory.
            for directory in [temporary] + [p for p in temporary.rglob('*')
                                             if p.is_dir() and not p.is_symlink()]:
                directory.chmod(0o755)
            # A private task directory is required; refuse an intervening user edit.
            if destination.exists() or destination.is_symlink():
                raise FileExistsError('destination appeared; preserve it')
            os.rename(temporary, destination)
            temporary = None
        finally:
            if temporary is not None:
                shutil.rmtree(temporary)
    return {'prefix': str(destination), 'archive_sha256': expected, 'selected': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive')
    parser.add_argument('sha256')
    args = parser.parse_args()
    print(json.dumps(stage(args.archive, args.sha256,
                           '/opt/oriole-experiments/mesa-g10')))
