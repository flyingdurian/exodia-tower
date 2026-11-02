"""Fail-closed Core-Five ORIGINAL CONCEPT recovery. No production promotion."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile
from PIL import Image, UnidentifiedImageError

LOCKED = {
    'idle': ('albedo_in_a_celestial_orbital_halo.png', '4de9758f8ea2f3f6f24af18d5e5dba8ac8c723c18afa7d55af6668456d2c6e9d'),
    'working': ('albedo_s_celestial_holographic_workstation.png', 'ec8e85610853591a0a46cdfac97c302b7359851681678ca4c64b179677ab7287'),
    'explaining': ('albedo_s_luminous_arcane_explanation.png', '162c999377522e4c93df8b7d286072d2ca8cc82cfa51b0af64410c174768a134'),
    'monitoring': ('albedo_in_a_celestial_command_halo.png', '4f75754980023b7596f7b0b9ccf9d36e695d936d40fb0efd7233c725d4be8d46'),
    'pointing': ('albedo_s_celestial_pointing_portrait.png', 'd55da7f4ca4e93a5d40592e97fe5c04cc6e3d9aaa8cbe8f24c64ee7e08de3b62'),
}
CONCEPT_SIZE = (1122, 1402)
MAX_MEMBER = 40 * 1024 * 1024
MAX_UNPACKED = 160 * 1024 * 1024

def digest(data): return hashlib.sha256(data).hexdigest()

def recover(bundle: Path, out_dir: Path, *, expected=LOCKED):
    """Verify SHA, PNG and shape before writing any of the five original files."""
    if not bundle.is_file(): raise FileNotFoundError(str(bundle))
    if not zipfile.is_zipfile(bundle): raise ValueError('invalid_zip')
    with zipfile.ZipFile(bundle) as z:
        listing = z.infolist()
        if sum(i.file_size for i in listing) > MAX_UNPACKED: raise ValueError('zip_size_limit')
        names, manifests = {}, []
        targets = {filename for filename, _ in expected.values()}
        for member in listing:
            path = PurePosixPath(member.filename.replace('\\','/'))
            if (member.filename.startswith('/') or '..' in path.parts or
                    any(part.endswith(':') for part in path.parts) or
                    member.file_size > MAX_MEMBER):
                raise ValueError('unsafe_zip_member:' + member.filename)
            if member.is_dir(): continue
            if path.name in targets:
                if path.name in names: raise ValueError('duplicate_basename:' + path.name)
                names[path.name] = member
            if 'manifest' in path.name.lower() and path.suffix.lower() in ('.json','.md','.yaml','.yml','.csv'):
                manifests.append(member)
        report = {'schema':'exodia.core5-source-recovery/v1',
                  'status':'FAIL','bundle_sha256':digest(bundle.read_bytes()),
                  'source_canvas':list(CONCEPT_SIZE),'native_production_canvas':[1536,1920],
                  'native_production_master_count':0,'states':{},'manifests':[]}
        valid = {}
        for state,(filename,wanted) in expected.items():
            rec = {'original_filename':filename,'expected_sha256':wanted,
                   'native_production':False,'status':'MISSING'}
            member = names.get(filename)
            if member:
                with z.open(member) as stream: data = stream.read(MAX_MEMBER+1)
                if len(data) > MAX_MEMBER: raise ValueError('zip_member_size_limit')
                actual = digest(data)
                rec['actual_sha256'] = actual
                if actual != wanted: rec['status'] = 'HASH_MISMATCH'
                else:
                    try:
                        with Image.open(io.BytesIO(data)) as img: img.verify()
                        with Image.open(io.BytesIO(data)) as img:
                            rec['canvas'] = list(img.size); kind = img.format
                        rec['format'] = kind
                        if kind == 'PNG' and tuple(rec['canvas']) == CONCEPT_SIZE:
                            rec['status'] = 'VERIFIED_CONCEPT'; valid[filename] = data
                        else: rec['status'] = 'INVALID_CONCEPT_CANVAS'
                    except (UnidentifiedImageError,OSError): rec['status'] = 'INVALID_PNG'
            report['states'][state] = rec
        for member in manifests:
            with z.open(member) as stream: data = stream.read(MAX_MEMBER+1)
            report['manifests'].append({'path':member.filename,
                                        'sha256':digest(data),'size_bytes':len(data)})
        # A handoff's specifically named canonical manifest is authoritative
        # too. Reject inconsistent claims before allowing extraction. Generic
        # synthetic-test manifests are not mistaken for this schema.
        canonical = [m for m in manifests if
                     PurePosixPath(m.filename).name ==
                     'EXODIA_CORE5_SOURCE_MANIFEST_2026-11-02.json']
        manifest_valid = True
        if len(canonical) > 1:
            raise ValueError('multiple_canonical_asset_manifests')
        if canonical:
            with z.open(canonical[0]) as stream:
                raw_manifest = stream.read(MAX_MEMBER+1)
            try:
                canonical_data = json.loads(raw_manifest)
            except (json.JSONDecodeError,UnicodeDecodeError) as ex:
                raise ValueError('unreadable_canonical_asset_manifest') from ex
            sources = canonical_data.get('sources',{})
            report['canonical_manifest_verification'] = {}
            for state,(filename,wanted) in expected.items():
                meta = sources.get(state) or {}
                passed = (
                    meta.get('filename') == 'sources/'+filename and
                    meta.get('sha256') == wanted and
                    meta.get('dimensions') == list(CONCEPT_SIZE) and
                    meta.get('format') == 'PNG' and
                    meta.get('release_approved') is False and
                    meta.get('dual_anchor_certified') is False)
                manifest_valid = manifest_valid and passed
                report['canonical_manifest_verification'][state] = (
                    'MATCH' if passed else 'MISMATCH')
            if not manifest_valid:
                report['errors']=['canonical_manifest_inconsistent_with_original_sources']
        else:
            report['canonical_manifest_verification']='NOT_INCLUDED'
        if len(valid) == len(expected) and manifest_valid:
            out_dir.mkdir(parents=True,exist_ok=True)
            for filename, data in valid.items():
                target = out_dir / filename
                if target.exists() and digest(target.read_bytes()) != digest(data):
                    raise ValueError('would_overwrite_different_original:' + filename)
                target.write_bytes(data)
            report['status'] = 'PASS_CONCEPT_RECOVERY_ONLY'
        return report

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--out-dir',type=Path,required=True)
    p.add_argument('--report',type=Path,required=True)
    args = p.parse_args()
    try: result = recover(args.bundle,args.out_dir)
    except (FileNotFoundError,ValueError,zipfile.BadZipFile) as ex:
        result = {'schema':'exodia.core5-source-recovery/v1','status':'BLOCKED',
                  'reason':str(ex),'native_production_master_count':0}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='PASS_CONCEPT_RECOVERY_ONLY' else 1

if __name__ == '__main__': raise SystemExit(main())
