"""Install an Albedo Phase 2 review ZIP; no production files changed."""
import argparse,hashlib,json,shutil,tempfile,zipfile
from pathlib import Path,PurePosixPath
DEST=Path('frontend/companions/review/kiko_wave2')
REFERENCE={
 'assets/benchmarks/emotions_approved_concept.png':'92bc46363077858bb0df',
 'assets/benchmarks/actions_set_A_approved_concept.png':'7b489427ca55c9c0d6f1',
 'assets/benchmarks/actions_set_B_revised_approved_concept.png':'17a3f1308be2293f3cac',
 'assets/benchmarks/loops_approved_concept.png':'686bbe9fe56f9006cf26',
 'assets/benchmarks/original_command_benchmark.png':'bfc233740851980021ea'}


def inspect(path):
 with zipfile.ZipFile(path) as archive:
  entries=[entry for entry in archive.infolist() if not entry.is_dir()]
  names=[e.filename for e in entries]
  if len(set(names))!=len(names):raise ValueError('duplicate path')
  for e in entries:
   parts=PurePosixPath(e.filename).parts
   if not parts or '..' in parts or e.filename.startswith('/') or '\\' in e.filename:raise ValueError('unsafe archive path')
   if e.file_size>32_000_000 or ((e.external_attr>>16)&0o170000)==0o120000:raise ValueError('oversized item or symlink')
  if sum(e.file_size for e in entries)>85_000_000:raise ValueError('archive too large')
  if 'manifest.json' not in names or 'albedo_portrait_wave2_review.html' not in names:raise ValueError('missing manifest or viewer')
  manifest=json.loads(archive.read('manifest.json'))
  if manifest.get('schema')!='exodia.albedo.portrait-wave2-review/v1' or manifest.get('character_id')!='kiko':raise ValueError('wrong companion or schema')
  if manifest.get('review_gate',{}).get('production_replacement_authorized') is not False:raise ValueError('unapproved release claim')
  if len(manifest.get('emotions',{}))!=20 or len(manifest.get('actions',{}))!=13:raise ValueError('incomplete states')
  for name,prefix in REFERENCE.items():
   if name not in names or not hashlib.sha256(archive.read(name)).hexdigest().startswith(prefix):raise ValueError('reference mismatch '+name)
  return {'can_install_review':True,'production_ready':False,'members':len(entries)}


def install(archive_path,app_root):
 inspect(archive_path)
 target=(Path(app_root)/DEST).resolve()
 if target.exists():raise FileExistsError('review exists; will not overwrite')
 target.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(archive_path) as zipf,tempfile.TemporaryDirectory(prefix='albedo-phase2-',dir=target.parent) as temporary:
  folder=Path(temporary)
  for entry in zipf.infolist():
   if entry.is_dir():continue
   name=entry.filename
   if not (name in ('manifest.json','README.md','albedo_portrait_wave2_review.html') or name.startswith('assets/')):continue
   dest=folder/name;dest.parent.mkdir(parents=True,exist_ok=True)
   with zipf.open(entry) as source,dest.open('wb') as output:shutil.copyfileobj(source,output)
  shutil.move(str(folder),str(target))
 return target


if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('zipfile',type=Path)
 p.add_argument('--app-root',type=Path,default=Path(__file__).resolve().parents[1])
 a=p.parse_args()
 print('Review installed:',install(a.zipfile,a.app_root))
 print('Open /assets/companions/review/kiko_wave2/albedo_portrait_wave2_review.html')
