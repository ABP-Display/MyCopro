"""Snapshot the simple database and documents together; no credentials in the ZIP.

Run from the host: python scripts/backup.py [--output-dir backups]
The archive is private and unencrypted. Restoration must be checked separately.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent.parent


def compose(*args, output=None):
    return subprocess.run(['docker','compose',*args],cwd=ROOT,stdout=output,check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'backups')
    args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    timestamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    target=args.output_dir/f'copro-simple-{timestamp}.zip'
    if target.exists():raise SystemExit('Une archive existe déjà à cette date.')
    with tempfile.TemporaryDirectory() as temporary:
        folder=Path(temporary)
        compose('pause','backend')
        try:
            with (folder/'database.dump').open('wb') as output:
                compose('exec','-T','db','pg_dump','-U','copro','-d','copro_simple','-Fc',output=output)
            with (folder/'documents.tar').open('wb') as output:
                compose('run','--rm','--no-deps','backend','python','-c',
                    "import sys,tarfile; archive=tarfile.open(fileobj=sys.stdout.buffer,mode='w|'); archive.add('/app/media',arcname='documents'); archive.close()",output=output)
        finally:
            compose('unpause','backend')
        (folder/'manifest.json').write_text(json.dumps({'format':'copro-simple-1','created_at':timestamp,'encrypted':False}),encoding='utf-8')
        with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as archive:
            for path in folder.iterdir():archive.write(path,path.name)
    print(f'Sauvegarde créée : {target.resolve()}')
    print('Archive non chiffrée : conservez-la hors accès public et contrôlez sa restauration.')


if __name__=='__main__':
    main()
