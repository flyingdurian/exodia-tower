"""Static Albedo portrait importer. Never manufactures images, landmarks or approvals."""
import argparse,json,shutil,tempfile
from pathlib import Path
from portrait_registry_audit import audit,within,digest,image_audit

def ingest(source:Path,destination:Path,ledger_path:Path,commit=False):
    source=source.resolve();destination=destination.resolve()
    if source==destination or source.is_relative_to(destination) or destination.is_relative_to(source):
        raise ValueError('source_and_destination_must_be_separate')
    if not (destination/'portrait_registry.json').is_file():raise ValueError('destination_registry_missing')
    ledger=json.loads(ledger_path.read_text())
    if ledger.get('schema')!='exodia.portrait-static-approval-ledger/v1':raise ValueError('approval_ledger_schema_mismatch')
    original=json.loads((destination/'portrait_registry.json').read_text())
    approvals=ledger.get('states',{})
    if len(original['states'])!=33 or set(approvals)!=set(original['states']):
        raise ValueError('approval_ledger_must_include_all_33_states')
    with tempfile.TemporaryDirectory(prefix='exodia_static_intake_') as temp:
        stage=Path(temp)/'kiko';shutil.copytree(destination,stage)
        registry=json.loads((stage/'portrait_registry.json').read_text())
        missing=[]
        for key,entry in registry['states'].items():
            image=within(source,entry['path'])
            registered=within(source,entry['registration_path'])
            row=approvals[key]
            if not image.is_file() or not registered.is_file() or not isinstance(row,dict):
                missing.append(key+':missing_image_registration_or_approval');continue
            image_sha=digest(image);registration_sha=digest(registered)
            if image_audit(image,image_sha):
                missing.append(key+':invalid_native_image');continue
            if row.get('image_sha256')!=image_sha or row.get('registration_sha256')!=registration_sha:
                missing.append(key+':approval_file_hash_mismatch');continue
            if row.get('approved_by')!='owner' or not isinstance(row.get('owner_confirmation_reference'),str) or len(row['owner_confirmation_reference'].strip())<8 or not row.get('reviewed_by'):
                missing.append(key+':owner_confirmation_or_reviewer_missing');continue
            target=within(stage,entry['path']);meta=within(stage,entry['registration_path'])
            target.parent.mkdir(parents=True,exist_ok=True)
            meta.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(image,target);shutil.copy2(registered,meta)
            entry.update(status='verified',sha256=image_sha,registration_sha256=registration_sha,
                         verified_by=row['reviewed_by'],owner_approval_reference=row['owner_confirmation_reference'])
        registry['release'].update(enabled=True,mode='static_portraits',
                  owner_static_release_reference=ledger.get('owner_static_release_reference'),
                  audit_status='pending_verified_release')
        (stage/'portrait_registry.json').write_text(json.dumps(registry,indent=2)+'\n')
        report=audit(stage/'portrait_registry.json') if not missing else {'status':'FAILED','errors':missing,'states_verified':0}
        passed=report['status']=='PASSED'
        if passed and commit:
            backup=destination.parent/(destination.name+'.backup_before_static_release')
            if backup.exists():raise ValueError('backup_exists_manual_cleanup_required')
            destination.rename(backup)
            try:shutil.move(str(stage),str(destination))
            except Exception:
                backup.rename(destination);raise
        return {'status':'PASSED' if passed else 'FAILED',
                'staged':passed and commit,'dry_run':not commit,
                'states_verified':report.get('states_verified',0),'errors':report['errors']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--registry-root',type=Path,required=True)
    p.add_argument('--approval-ledger',type=Path,required=True)
    p.add_argument('--commit',action='store_true')
    p.add_argument('--report',type=Path)
    x=p.parse_args()
    try:result=ingest(x.source,x.registry_root,x.approval_ledger,commit=x.commit)
    except (OSError,ValueError,TypeError) as e:result={'status':'FAILED','errors':[str(e)],'staged':False}
    rendered=json.dumps(result,indent=2)+'\n';print(rendered)
    if x.report:x.report.parent.mkdir(parents=True,exist_ok=True);x.report.write_text(rendered)
    return 0 if result['status']=='PASSED' else 1

if __name__=='__main__':raise SystemExit(main())
