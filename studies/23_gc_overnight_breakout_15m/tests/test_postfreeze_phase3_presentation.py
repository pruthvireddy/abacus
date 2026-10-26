"""Additional final-schema presentation refusals; no historical outcome reads."""
import csv
import base64
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
import test_phase3_cloud_figures as cloud_fixture
import test_phase3_report_supplements as table_fixture
import phase3_cloud_figures as render
import phase3_report_supplements as supplements


class FinalCloudAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.f=cloud_fixture.Phase3CloudFigureTests(methodName='test_only_requested_summary_groups_consume_example_sources')
        self.f.setUp();self.addCleanup(self.f.doCleanups)

    def test_computed_but_unavailable_cloud_and_missing_raw_minute_preserve_gaps(self):
        self.f.cloud[4]['feature_valid']='False'
        self.f.minutes[12].update(open='',high='',low='',close='',usable='False')
        self.f.write('selected-example-cloud',self.f.cloud);self.f.write('selected-example-minutes',self.f.minutes)
        d=self.f.draft();render.add_cloud_examples(d,[])
        record=d.figures[0];panel=record['plot_encoding']['panels'][0]
        self.assertEqual(panel['series'][1]['source_rows'],list(range(7)))
        self.assertEqual(panel['series'][1]['validity_columns'],['usable','feature_valid'])
        self.assertEqual(panel['series'][1]['segments'],[[0,1,2],[5,6]])
        self.assertEqual(panel['series'][0]['segments'],[list(range(12)),list(range(13,35))])
        tree=ET.fromstring(d.files[record['svg_path']]);projection=self.f.projection(d)
        cloud_fixture.check.verify_cloud_path(record,tree,projection)
        panel['series'][1]['validity_columns']=['usable']
        with self.assertRaisesRegex(ValueError,'unavailable computed cloud'):cloud_fixture.check.verify_cloud_path(record,tree,projection)

    def test_x1_first_frozen_candle_starts_level_before_second_confirmation(self):
        c=self.f.case
        c.update(id='x1-loss-saved-long',policy='X1',mode='standardized',leg='original',kind='loss_saved',parent_entry=cloud_fixture.clock(0),parent_fill_upper=cloud_fixture.clock(1),frozen_level_contact_open=cloud_fixture.clock(5),frozen_level_available_at=cloud_fixture.clock(5),legs=[c['legs'][0]])
        for rows in (self.f.minutes,self.f.cloud):
            for row in rows:row['case_id']=c['id']
        self.f.write('selected-example-cloud',self.f.cloud);self.f.write('selected-example-minutes',self.f.minutes)
        (self.f.stage/'example-selection.json').write_text(json.dumps(self.f.selection))
        d=cloud_fixture.Draft(cloud_fixture.SavedInputs(self.f.stage),'synthetic',cloud_fixture.ReportSpec('earlier-exits','summary'));render.add_cloud_examples(d,[])
        record=d.figures[0];panel=record['plot_encoding']['panels'][0]
        level=next(x for x in panel['levels'] if x['id']=='frozen-contact')
        self.assertEqual(level['start_time'],cloud_fixture.clock(5))
        self.assertEqual(level['end_time'],cloud_fixture.clock(15))
        self.assertTrue(any(x['id']=='frozen-origin-clock' for x in panel['annotations']))
        cloud_fixture.check.verify_cloud_path(record,ET.fromstring(d.files[record['svg_path']]),self.f.projection(d))

    def test_exact_selected_case_roster_and_png_byte_pin_are_independent_requirements(self):
        self.f.selection['run_id']=self.f.stage.name
        (self.f.stage/'example-selection.json').write_text(json.dumps(self.f.selection))
        d=cloud_fixture.Draft(cloud_fixture.SavedInputs(self.f.stage),self.f.stage.name,cloud_fixture.ReportSpec('ema20-support','summary'))
        sections=[];render.add_cloud_examples(d,sections)
        # A synthetic pixel proves byte identity only; actual raster QA is separate.
        png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jDPkAAAAASUVORK5CYII=')
        d.complete_png(d.figures[0]['path'],png)
        projection=self.f.projection(d);mapping=d.source_map()
        cloud_fixture.check.figures(dict(sections=sections),mapping,projection)
        mapping['figures'][0]['selection_case_pointers'].append('/cases/0')
        with self.assertRaisesRegex(ValueError,'balanced saved-case figure roster'):cloud_fixture.check.figures(dict(sections=sections),mapping,projection)
        mapping['figures'][0]['selection_case_pointers'].pop()
        mapping['figures'][0]['image_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'rendered PNG bytes'):cloud_fixture.check.figures(dict(sections=sections),mapping,projection)


class FinalConfluenceProjectionTests(unittest.TestCase):
    def setUp(self):
        self.f=table_fixture.Phase3SupplementTests(methodName='test_module_never_imports_any_numerical_producer')
        self.f.setUp();self.addCleanup(self.f.doCleanups)

    def test_every_saved_level_state_event_year_session_side_cell_is_retained(self):
        d=self.f.draft('other-cloud-uses','summary');sections=[];supplements.add_supplements(d,sections)
        self.f.verify_tables(d,sections)
        reports=[s for s in sections if s['id'].endswith('confluence-rates')]
        self.assertEqual([len(s['rows']) for s in reports],[135,135])
        self.assertEqual({r['c0'] for s in reports for r in s['rows']},{'H','L','M'})
        self.assertEqual({r['c1'] for s in reports for r in s['rows']},{'yes','no','unknown'})
        self.assertEqual({r['c2'] for s in reports for r in s['rows']},set(supplements.CONTACT_EVENTS))
        files=[f for f in d.download_entries if d.sources[f['source']['artifact']]['original_stage_source_path']=='tables/confluence.csv']
        self.assertEqual([f['rowCount'] for f in files],[6750,6750])
        self.assertTrue(all(len(f['columns'])==18 for f in files))
        mapping=d.source_map()
        pub=self.f.stage/'projection'
        projection=table_fixture.check.Projection(self.f.stage,pub,mapping)
        self.assertGreater(table_fixture.check.downloads(dict(source=dict(runId='synthetic'),downloads=d.download_entries),mapping,projection),0)
        selection=[s for s in d.sources.values() if s['original_stage_source_path']=='tables/confluence.csv' and 'year' not in s['selectors']]
        self.assertEqual(sum(len(s['selected_source_rows']) for s in selection),13500)
        self.assertEqual(set(selection[0]['selected_source_rows'])&set(selection[1]['selected_source_rows']),set())


if __name__=='__main__':unittest.main()
