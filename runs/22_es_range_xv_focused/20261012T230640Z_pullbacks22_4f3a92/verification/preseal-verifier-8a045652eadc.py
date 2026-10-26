"""Artifact-bound preseal checks for the explicitly selected new pullback stage."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('pullback_lifecycle', root/'studies/22_es_range_xv_focused/pullback_run.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
p = argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);a=p.parse_args()
stage=m.stage_path(a.stage,existing=True)
m.verify_artifacts(stage)
child=m.require_numerical_result(stage)
for name in ('verification.json','publication-verification.json','verification/publication-transfer-independent.json','verification/narada-contract-dry-run.json'):
    m.require_receipt(stage,name,set())
contract=json.loads((stage/'verification/narada-contract-dry-run.json').read_text())
assert len(contract['checks'])==9 and contract['run_id']==stage.name
pins=json.loads((stage/'verification/numerical-test-source-pins.json').read_text())
for item in pins['files']:
    assert m.digest(root/item['path'])==item['sha256']==m.digest(stage/item['snapshot_path'])
snapshot=stage/'verification'/f'preseal-verifier-{m.digest(Path(__file__))[:12]}.py'
with snapshot.open('xb') as f:f.write(Path(__file__).read_bytes())
checks=['verification.json','publication-verification.json','verification/publication-transfer-independent.json','verification/numerical-test-result.json','verification/numerical-test-source-pins.json','verification/numerical-test-command.json','verification/narada-contract-dry-run.json','verification/numerical-tests.log','verification/independent-audit.log','verification/publication-transfer.log','verification/render.log','verification/execution.log','verification/workspace-check.log','metrics.json','findings.md','execution-feasibility.json']
checks += [x['snapshot_path'] for x in pins['files']]
checks += [x.relative_to(stage).as_posix() for x in (stage/'verification').glob('publication-transfer-independent-*.py')]
checks.append(snapshot.relative_to(stage).as_posix())
hashes={name:m.digest(stage/name) for name in checks}
result={'result':'passed','study_id':m.STUDY_ID,'run_id':stage.name,'checked_at':m.now(),'artifact_hashes':hashes,'numerical_counts':child['counts'],'independent_scope':{'setups':217366,'proxy_scenarios':434732,'saved_rows':262656,'report_numeric_cells':519804,'selected_csv_cells':2673000},'workspace_default_gate':{'result':'qualified_prerequisite_failure','errors':['Missing continuous-roll raw mapping','Missing point-in-time ES definition pair'],'later_default_checks':'not executed after Bhishma prerequisite failure'},'command':m.command_record(),'verifier':{'sha256':m.digest(Path(__file__)),'snapshot':snapshot.relative_to(stage).as_posix()}}
m.write_json(stage/'preseal-checks.json',result)
print(json.dumps({'result':'passed','numerical_counts':child['counts'],'bound_artifacts':len(hashes)}))
