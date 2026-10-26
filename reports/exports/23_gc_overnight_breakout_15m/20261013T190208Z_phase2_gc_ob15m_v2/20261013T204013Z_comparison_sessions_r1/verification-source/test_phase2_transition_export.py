"""Rejection fixtures for new post-seal exact transition coverage."""
import ast
import importlib.util
from pathlib import Path
import tempfile
import unittest

FILE=Path(__file__).resolve().parents[1]/"phase2_verify_transition_export.py"
spec=importlib.util.spec_from_file_location("new_transition_transfer",FILE)
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)


class PostsealTransitionTests(unittest.TestCase):
    def fixture(self):
        rows=[dict(year="all",side="combined",count="0",unknown="1",transition="p"),dict(year="2026",side="upper-first",count="2",unknown="0",transition="p"),dict(year="2025",side="lower-first",count="1",unknown="0",transition="other")]
        report=dict(sections=[dict(id="matrix",kind="table")])
        bindings=[dict(section="matrix",original_stage_source_path="tables/transitions.csv",original_source_row=i,original_source_column=c) for i in range(2) for c in ("year","side","count","unknown")]
        return report,dict(bindings=bindings),rows

    def test_unknown_and_partial_year_zero_rows_are_required(self):
        report,mapping,rows=self.fixture()
        count=checker.source_display_coverage(report,mapping,"tables/transitions.csv",rows,lambda r:r["transition"]=="p",("year","side","count","unknown"))
        self.assertEqual(count,8)

    def test_annual_source_row_omission_is_rejected(self):
        report,mapping,rows=self.fixture();mapping["bindings"]=[b for b in mapping["bindings"] if b["original_source_row"]==0]
        with self.assertRaisesRegex(ValueError,"complete displayed"):checker.source_display_coverage(report,mapping,"tables/transitions.csv",rows,lambda r:r["transition"]=="p",("year","count"))

    def test_unknown_cannot_be_hidden_in_an_unrequested_column(self):
        report,mapping,rows=self.fixture();mapping["bindings"]=[b for b in mapping["bindings"] if b["original_source_column"]!="unknown"]
        with self.assertRaisesRegex(ValueError,"unknown"):checker.source_display_coverage(report,mapping,"tables/transitions.csv",rows,lambda r:r["transition"]=="p",("count","unknown"))

    def test_metric_instead_of_saved_table_rows_does_not_cover_matrix(self):
        report,mapping,rows=self.fixture();report["sections"][0]["kind"]="metrics"
        with self.assertRaisesRegex(ValueError,"complete displayed"):checker.source_display_coverage(report,mapping,"tables/transitions.csv",rows,lambda r:r["transition"]=="p",("count",))

    def test_short_presentation_keys_preserve_complete_original_column_lineage(self):
        report,mapping,rows=self.fixture()
        for binding in mapping['bindings']:binding['key']={'year':'y','side':'d','count':'n','unknown':'u'}[binding['original_source_column']]
        self.assertEqual(checker.source_display_coverage(report,mapping,'tables/transitions.csv',rows,lambda r:r['transition']=='p',('year','side','count','unknown')),8)

    def test_two_downloads_require_lossless_partition_and_private_original_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/"source";publication=Path(folder)/"pub";(source/"tables").mkdir(parents=True);(publication/"downloads").mkdir(parents=True);(publication/"tables").mkdir()
            original=b'year,count,unknown\r\nall,0,1\r\n';(source/"tables/transitions.csv").write_bytes(original);(publication/"tables/master.csv").write_bytes(original)
            for name in ('original','boundary'):(publication/'downloads'/(name+'.csv')).write_bytes(b'projection')
            rows=[dict(transition='breakout_to_breach'),dict(transition='breakout_to_candidate_entry:reclaim-q000'),dict(transition='breach_to_candidate_entry:reclaim-q000')]
            report=dict(downloads=[dict(id=name,path='downloads/'+name+'.csv') for name in ('original','boundary')])
            mapping=dict(downloads=[dict(id='original',original_stage_source_path='tables/transitions.csv',original_source_rows=[1],columns=['transition']),dict(id='boundary',original_stage_source_path='tables/transitions.csv',original_source_rows=[0,2],columns=['transition'])],source_artifacts=[dict(path='tables/master.csv',original_stage_source_path='tables/transitions.csv',selected_source_rows=[0,1,2])])
            self.assertEqual(checker.transition_download_partition(source,publication,report,mapping,rows)['total_rows'],3)
            mapping['downloads'][1]['original_source_rows']=[0,1,2]
            with self.assertRaisesRegex(ValueError,'two ordered'):checker.transition_download_partition(source,publication,report,mapping,rows)
            mapping['downloads'][1]['original_source_rows']=[0,2]
            (publication/'tables/master.csv').write_bytes(original.replace(b'\r\n',b'\n'))
            with self.assertRaisesRegex(ValueError,'byte identity'):checker.transition_download_partition(source,publication,report,mapping,rows)

    def test_no_numerical_producer_import_or_existing_source_mutation(self):
        names=[]
        for node in ast.walk(ast.parse(FILE.read_text())):
            if isinstance(node,ast.Import):names.extend(a.name for a in node.names)
            elif isinstance(node,ast.ImportFrom):names.append(node.module)
        self.assertFalse(any("engine" in n or "metrics" in n or "publish" in n for n in names))


if __name__=="__main__":unittest.main()
