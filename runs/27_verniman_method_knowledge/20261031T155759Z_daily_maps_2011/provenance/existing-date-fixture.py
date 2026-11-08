#!/usr/bin/env python3
"""Independent bounded 2015 title-date/review guard fixtures against the real adapter."""
import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import html as html_lib
from datetime import date
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/pruthvi/Documents/projects/abacus')


def run(root):
    spec=importlib.util.spec_from_file_location('guard_adapter2015',root/'studies/27_verniman_method_knowledge/capture_retained_daily_maps.py')
    adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
    results={}
    with tempfile.TemporaryDirectory(prefix='daily-map-2015-date-guards-') as temp:
        base=Path(temp)
        def write(relative,raw):
            p=base/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            return {'path':relative,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        review=write('input/review.json',b'{"kind":"synthetic2015review","status":"passed"}\n')
        def prepare(title,stamp,*,body='Market Context: Opening auction. Trading Plan: be a buyer above 2000.',daily=True,status=None,warnings=None,url='https://verniman.blogspot.com/2015/fixture.html',review_title=None,date_order=None,reason=None,atom=False,published='2015-10-28T09:01:00.001-04:00',corroborating=None):
            record_title=title.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            html=('<html><body><a name="12345"></a><h3 class="post-title">'+record_title+'</h3><div class="post-body entry-content">'+body+'</div></body></html>').encode()
            hr=write('input/source.html',html);pr=write('input/post.json',json.dumps({'source_post_id':'12345','title':title}).encode())
            post={'url':url,'title':title,'session_date':stamp,'html':hr,'post_record':pr,'source_post_id':'12345','source_format':'archived_html','session_date_method':'synthetic_explicit_review','session_date_source_text':title,'images':[],'date_warnings':(['Source title omits month/day; retained undated.'] if stamp is None else []) if warnings is None else warnings,'year_evidence':{'year':2015,'method':'synthetic_independent_year_review'},'reviewed_daily_plan':daily,'date_review':{'status':status or ('undated_title_missing_month_day' if stamp is None else 'dated_title'),'source_title':title if review_title is None else review_title},'captured_at':'2026-10-31T00:00:00Z','archive_observed_at':'2015-12-31T20:00:00Z','archive_url':'https://web.archive.org/web/20151231200000id_/http://verniman.blogspot.com/2015/fixture.html'}
            if date_order is not None:post['date_review']['date_order']=date_order
            if reason is not None:post['date_review']['reason']=reason
            if corroborating is not None:post['date_review']['corroborating_published_at']=corroborating
            if atom:
                entry_id='tag:blogger.com,1999:blog-6141192815370358651.post-12345'
                xml=('<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>'+entry_id+'</id><title>'+html_lib.escape(title)+'</title><published>'+published+'</published><updated>'+published+'</updated><link rel="alternate" href="'+html_lib.escape(url,quote=True)+'"/><content type="html">'+html_lib.escape(body)+'</content></entry></feed>').encode()
                ar=write('input/feed.xml',xml);er=write('input/entry.json',json.dumps({'id':entry_id,'title':title}).encode())
                post.update(source_format='archived_atom_feed',html=None,atom=ar,entry_record=er,body_html=body,source_entry_selector=entry_id,source_entry_id=entry_id,source_feed_entry_ordinal=1,source_published_at=published)
            document={'source':'verniman','requested_start_date':'2015-01-01','anchor_session_date':'2015-12-31','posts':[post],'files':[],'traversal':[],'chronology_review':review,'collection_completion_review':review,'archive_capture_manifest':review,'stop_reason':'synthetic_fixture_only'}
            record=write('input/collection.json',json.dumps(document).encode())
            return adapter.Adapter(base).prepare(base/record['path'],date(2015,1,1),date(2015,12,31),record['sha256'])
        def accepts(name,*args,**kwargs):
            _,prepared=prepare(*args,**kwargs);assert len(prepared)==1;results[name]=True
        def rejects(name,*args,**kwargs):
            try:prepare(*args,**kwargs)
            except (ValueError,TypeError):results[name]=True
            else:raise AssertionError('guard accepted forbidden case: '+name)
        accepts('outlook_month_day_accepted','Outlook 12/31','2015-12-31')
        accepts('opening_mmdd_accepted_with_explicit_daily_review','Opening 0407','2015-04-07')
        accepts('opening_print_month_day_accepted_with_explicit_daily_review','Opening Print 04/07','2015-04-07')
        accepts('unambiguous_day_month_requires_explicit_review','Outlook 28/10','2015-10-28',date_order='day_month',reason='Synthetic independently reviewed literal day/month source date.',atom=True,corroborating='2015-10-28T09:01:00.001-04:00')
        rejects('day_month_requires_exact_atom_source','Outlook 28/10','2015-10-28',date_order='day_month',reason='Cannot claim a feed corroboration for HTML.',corroborating='2015-10-28T09:01:00.001-04:00')
        rejects('day_month_requires_publication_corroboration','Outlook 28/10','2015-10-28',date_order='day_month',reason='Missing corroborating entry publication.',atom=True)
        rejects('day_month_rejects_changed_publication_corroboration','Outlook 28/10','2015-10-28',date_order='day_month',reason='Wrong corroborating entry publication.',atom=True,corroborating='2015-10-29T09:01:00.001-04:00')
        rejects('day_month_rejects_published_date_conflict','Outlook 28/10','2015-10-28',date_order='day_month',reason='Source publication differs from assigned title date.',atom=True,published='2015-10-29T09:01:00.001-04:00',corroborating='2015-10-29T09:01:00.001-04:00')
        rejects('unreviewed_reversed_date_rejected','Outlook 28/10','2015-10-28')
        rejects('ambiguous_reversal_is_not_allowed','Outlook 12/11','2015-11-12',date_order='day_month',reason='Cannot resolve ambiguous month/day by this path.')
        rejects('day_month_review_requires_reason','Outlook 28/10','2015-10-28',date_order='day_month',reason='')
        _,prepared=prepare('Opening Print',None,url='https://verniman.blogspot.com/2015/01/opening-print-0107.html')
        assert prepared[0][0]['session_date'] is None;results['missing_title_date_remains_null_despite_dated_url']=True
        rejects('url_date_alone_cannot_assign_session','Opening Print','2015-01-07',url='https://verniman.blogspot.com/2015/01/opening-print-0107.html')
        rejects('title_assigned_date_conflict_rejected','Outlook 12/31','2015-12-30')
        rejects('undated_body_date_conflict_rejected','Opening Print',None,body='Outlook 01/07: Opening auction plan.')
        rejects('opening_new_grammar_without_explicit_daily_review_rejected','Opening 0407','2015-04-07',daily=False)
        rejects('undated_without_warning_rejected','Opening Print',None,warnings=[])
        rejects('review_title_does_not_become_opening_map','Review 08/14','2015-08-14')
        rejects('multiple_explicit_title_dates_rejected','Outlook 01/05 Opening 0106','2015-01-05')
        rejects('date_review_source_title_drift_rejected','Opening 0407','2015-04-07',review_title='Opening 0408')
    assert all(results.values())
    return {'status':'passed','scope':'Synthetic adapter title-date/classification guards only; no historical source dates inferred.','checks':results,'check_count':len(results)}


if __name__=='__main__':
    print(json.dumps(run(ROOT),indent=2))
