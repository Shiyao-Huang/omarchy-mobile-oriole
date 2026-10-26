"""Failure/isolation checks; not a GPU or target ABI test."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('stage', root / 'tools/stage-mesa-candidate.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def archive(path, entries):
    with tarfile.open(path, 'w:gz') as tf:
        for name, kind, value in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            if kind == tarfile.REGTYPE:
                b = value.encode(); info.size = len(b)
                tf.addfile(info, io.BytesIO(b))
            else:
                info.linkname = value
                tf.addfile(info)
    return hashlib.sha256(path.read_bytes()).hexdigest()

with tempfile.TemporaryDirectory() as name:
    d = Path(name); a = d/'input.tar.gz'; target = d/'prefix'
    good = [('lib/libEGL.so.1', tarfile.REGTYPE, 'candidate'),
            ('lib/libEGL.so', tarfile.SYMTYPE, 'libEGL.so.1')]
    bad = [[('../escape', tarfile.REGTYPE, 'x')],
           [('/escape', tarfile.REGTYPE, 'x')],
           [('lib/escape', tarfile.SYMTYPE, '../../escape')],
           [('lib/escape', tarfile.SYMTYPE, '/tmp')],
           [('lib/device', tarfile.CHRTYPE, '')],
           [('lib/hardlink', tarfile.LNKTYPE, 'lib/target')],
           good + [('lib/libEGL.so', tarfile.REGTYPE, 'duplicate')],
           [('lib/alias', tarfile.SYMTYPE, 'real'),
            ('lib/alias/evil', tarfile.REGTYPE, 'x')],
           [('lib/missing', tarfile.SYMTYPE, 'absent')]]
    for entries in bad:
        digest = archive(a, entries)
        try:
            module.stage(a, digest, target)
        except (ValueError, OSError):
            pass
        else:
            raise AssertionError('unsafe archive accepted')
        assert not target.exists() and not list(d.glob('.mesa-stage-*'))
    digest = archive(a, good)
    try:
        module.stage(a, '0'*64, target)
    except ValueError:
        pass
    else:
        raise AssertionError('bad digest accepted')
    module.stage(a, digest, target)
    assert (target/'lib/libEGL.so').read_text() == 'candidate'
    assert target.stat().st_mode & 0o777 == 0o755
    assert (target/'lib').stat().st_mode & 0o777 == 0o755
    (target/'manual').write_text('preserve')
    try:
        module.stage(a, digest, target)
    except FileExistsError:
        pass
    else:
        raise AssertionError('existing prefix overwritten')
    assert (target/'manual').read_text() == 'preserve'
print('PASS staging: digest, traversal, links, devices, duplicates, failed cleanup, existing/manual files preserved')
