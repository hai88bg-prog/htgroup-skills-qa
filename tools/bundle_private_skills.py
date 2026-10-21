#!/usr/bin/env python3
"""Make/verify a LOCAL private transfer ZIP from selected skill directories.
Never uploads, contacts GitHub, or changes any input skill file.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'.md', '.py', '.json', '.yaml', '.yml', '.txt', '.sh', '.toml', '.xml'}
BLOCK_DIRS = {'.git', '__pycache__', '.venv', 'venv', 'node_modules', 'SCENES', 'CLIPS', 'film-data', 'private', 'outputs'}
BLOCK_NAMES = {'.env', '.env.local', '.env.production', 'credentials.json', 'secrets.json', '.npmrc'}
KEY_PATTERN = re.compile(r'(?:ghp_|gho_|github_pat_)[A-Za-z0-9_]{12,}|(?:sk-|AIza)[A-Za-z0-9_\-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----')
MAX_FILE = 5 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build(skills, output):
    entries = {}
    names = set()
    for raw in skills:
        folder = Path(raw).expanduser().resolve()
        if not (folder / 'SKILL.md').is_file():
            raise ValueError(f'Not a skill folder (SKILL.md missing): {folder}')
        if folder.name in names:
            raise ValueError(f'Duplicate skill folder name: {folder.name}')
        names.add(folder.name)
        for f in sorted(folder.rglob('*')):
            if not f.is_file() or f.is_symlink():
                continue
            rel = f.relative_to(folder)
            if any(part in BLOCK_DIRS or part.startswith('.') for part in rel.parts):
                continue
            if f.name in BLOCK_NAMES or f.suffix.lower() not in ALLOWED:
                continue
            if f.stat().st_size > MAX_FILE:
                raise ValueError(f'Oversized file; review manually: {f}')
            data = f.read_bytes()
            if KEY_PATTERN.search(data.decode('utf-8', errors='ignore')):
                raise ValueError(f'Potential secret in file; refuse private package: {f}')
            entries[f'skills/{folder.name}/{rel.as_posix()}'] = data
    for local, arc in ((ROOT/'qa.py', 'HTGROUP_QA/qa.py'),
                       (ROOT/'contracts/review-31.json', 'HTGROUP_QA/contracts/review-31.json')):
        entries[arc] = local.read_bytes()
    output = Path(output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError('Refuse to overwrite existing ZIP: '+str(output))
    manifest = {'schema':'htgroup-private-skill-transfer-v1',
                'files': {k: digest(v) for k, v in sorted(entries.items())},
                'warning': 'PRIVATE archive. Never upload it to the public QA repository.'}
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for key, data in sorted(entries.items()): z.writestr(key, data)
        z.writestr('MANIFEST_SHA256.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    return len(entries), output


def verify(path):
    with zipfile.ZipFile(path, 'r') as z:
        names = z.namelist()
        if len(names) != len(set(names)) or 'MANIFEST_SHA256.json' not in names:
            raise ValueError('Duplicate paths or missing manifest')
        manifest = json.loads(z.read('MANIFEST_SHA256.json'))
        expected = manifest['files']
        if sorted(expected) != sorted(n for n in names if n != 'MANIFEST_SHA256.json'):
            raise ValueError('Archive entries do not match manifest')
        for name, sha in expected.items():
            if name.startswith('/') or '..' in Path(name).parts:
                raise ValueError('Unsafe ZIP entry')
            if digest(z.read(name)) != sha:
                raise ValueError('Checksum mismatch: '+name)
        return len(expected)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--skill', action='append', default=[], help='A local skill folder with SKILL.md; repeat for steps 3–8')
    p.add_argument('--output', help='Destination local private ZIP, not GitHub')
    p.add_argument('--verify', help='Verify an already exported ZIP')
    a = p.parse_args(argv)
    try:
        if a.verify:
            count = verify(a.verify)
            print('PRIVATE_ZIP_HASHES_VERIFIED', count, a.verify)
            return 0
        if not a.skill or not a.output:
            p.error('Use --skill PATH --output FILE.zip, or --verify FILE.zip')
        count, path = build(a.skill, a.output)
        print('PRIVATE_ZIP_CREATED', str(path), 'FILE_COUNT', count)
        print('DO_NOT_UPLOAD_THIS_ZIP_TO_PUBLIC_GITHUB')
        return 0
    except (ValueError, OSError, zipfile.BadZipFile) as e:
        print('ERROR', e, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
