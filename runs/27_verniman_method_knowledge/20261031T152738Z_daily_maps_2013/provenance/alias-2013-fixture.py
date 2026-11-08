"""Only the observed .com.ar alias is normalized; archive transport remains exact."""
import importlib.util,json,sys,tempfile
from pathlib import Path
sys.dont_write_bytecode=True
root=Path('/Users/pruthvi/Documents/projects/abacus')
spec=importlib.util.spec_from_file_location('alias2013',root/'studies/27_verniman_method_knowledge/recover_archived_daily_maps.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checks={}
assert m.canonical('http://verniman.blogspot.com.ar:80/2013/03/a.html?m=1')=='https://verniman.blogspot.com/2013/03/a.html'
checks['observed_country_alias_and_port_normalize_identity']=True
assert m.canonical('http://verniman.blogspot.com:80/2013/03/a.html')=='https://verniman.blogspot.com/2013/03/a.html'
checks['original_host_identity_preserved']=True
for host in ['verniman.blogspot.co.uk','verniman.blogspot.com.evil.example','example.com']:
    try:m.canonical('https://'+host+'/2013/03/a.html')
    except ValueError:pass
    else:raise AssertionError(host)
checks['unobserved_hosts_rejected']=True
assert m.Recovery.archive_key('https://web.archive.org/web/20130101000000id_/http://verniman.blogspot.com.ar:80/')=='https://web.archive.org/web/20130101000000id_/http://verniman.blogspot.com.ar/'
checks['reuse_key_removes_only_observed_default_port']=True
with tempfile.TemporaryDirectory(prefix='verniman-alias-fixture-') as temp:
    path=Path(temp)/'index.json';original='http://verniman.blogspot.com.ar:80/2013/03/a.html'
    path.write_text(json.dumps([['timestamp','original','statuscode','mimetype','digest'],['20140501000000',original,'200','text/html','fixture']]))
    _,rows=m.index_items(path,None,root,2013)
    assert rows[0]['archive_source_url']==original and rows[0]['archive_index_row']['original']==original
    assert rows[0]['url']=='https://verniman.blogspot.com/2013/03/a.html'
checks['exact_index_archive_transport_and_raw_row_retained']=True
print(json.dumps({'status':'passed','checks':checks,'check_count':len(checks),'network_requests':0,'temporary_fixture_only':True},indent=2))
