"""Exact source transfer and saved decision tests for independent synthesis QA."""
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location("synthesis_independent",Path(__file__).resolve().parents[1]/"phase2_verify_synthesis.py")
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)


class IndependentSynthesisTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.stage=Path(self.tmp.name);(self.stage/"tables").mkdir()
        paired=[dict(year="all",session="all",side=side,family=family,policy="rule",episodes="0",complete_pairs="0",missing_pairs="0",fills="0",completed="0",mean_difference="",difference_low="",difference_high="",adjusted_low="",adjusted_high="") for side,family in (("combined","primary"),("upper-first","protected"),("lower-first","protected"))]
        trade=[dict(year="all",session="all",side="combined",policy="rule",executable_fills="0",completed="0",censored="0",wins="0",losses="0",breakevens="0",net_dollars="0.0",mean_net_dollars="",profit_factor="",max_drawdown_dollars="0.0")]
        occurrence=[dict(year="all",session="all",side=side,horizon="original_session",event="touch",episodes="0",known_events="0",known_denominator="0",unknown="0",rate="",lower_bound="",upper_bound="",mean_exposure_minutes="",mean_elapsed_minutes="") for side in ("upper-first","lower-first")]
        account=[dict(year="all",session="all",side="combined",policy="baseline",mode="original",episodes="0",signals="0",eligible_loss="0",original_fills="0",second_fills="0",quantity_skips="0",completed_pairs="0",full_recovery="0",unknown="0",net_dollars="0.0")]
        self.tables={"paired":paired,"trade-cohorts":trade,"occurrence":occurrence,"account":account}
        pins={}
        for name,rows in self.tables.items():
            path=self.stage/"tables"/(name+".csv")
            with path.open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            pins[name]=dict(path="tables/"+name+".csv",sha256=checker.digest(path))
        self.expected=checker.expected_bindings(self.tables)
        self.mapping=dict(status="prepared",tables=pins,bindings=self.expected,publications=[])
        for name,value in (("selection",dict(decision="no_qualifier",selected_policy=None)),("assessment",dict(decision="baseline_retained"))):
            path=self.stage/(name+".json");path.write_text(json.dumps(value))
            self.mapping[name]=dict(path=path.name,sha256=checker.digest(path))
        pubs=[]
        for i in range(23):
            folder=self.stage/"publications"/str(i);folder.mkdir(parents=True)
            path=folder/"publication.json";report=dict(id=str(i),title="Report "+str(i),source=dict(runId=self.stage.name));path.write_text(json.dumps(report))
            pubs.append(dict(id=str(i),title=report["title"],source=str(path.relative_to(self.stage)),sha256=checker.digest(path)))
        self.mapping["publications"]=pubs
        q="not pristine holdouts Phase3 remain uncomputed whole contracts Known no-fill is zero unknown execution remains unavailable Actual-entry trade performance has a different cohort anchor tick ordering and native TradingView replay remain unverified Assumed costs are not the user's broker charges"
        self.md=q+"\nSaved validation decision: `no_qualifier`; selected policy: `Unavailable`.\nSaved later assessment: `baseline_retained`.\n"+"\n".join("| "+b["rendered"]+" |" for b in self.expected)+"\n"+"\n".join("- ["+p["title"]+"]("+p["source"]+")" for p in pubs)
        self.html=q+"<p>Validation: no_qualifier. Selected: Unavailable. Later: baseline_retained.</p><table>"+"".join("<tr><td>"+b["rendered"]+"</td></tr>" for b in self.expected)+"</table>"+"".join('<a href="'+p["source"]+'">'+p["title"]+'</a>' for p in pubs)
        self.advice=q+"\nSaved validation decision: `no_qualifier`; selected rule: `Unavailable`. Later assessment: `baseline_retained`.\n"
        self.save()

    def save(self):
        for name,text in (("report.md",self.md),("report.html",self.html),("advice.md",self.advice)):(self.stage/name).write_text(text)
        self.mapping["outputs"]={name:checker.digest(self.stage/name) for name in ("report.md","report.html","advice.md")}
        (self.stage/"report-source-map.json").write_text(json.dumps(self.mapping))

    def test_empty_support_nulls_and_actual_zero_cells_roundtrip(self):
        receipt=checker.verify(self.stage)
        self.assertEqual(receipt["cells"],len(self.expected));self.assertIsNone(receipt["selected_policy"])

    def test_matching_rounded_display_does_not_replace_raw_saved_string(self):
        self.html=self.html.replace("<td>0.0</td>","<td>0</td>",1);self.save()
        with self.assertRaisesRegex(ValueError,"HTML saved"):checker.verify(self.stage)

    def test_source_binding_cannot_omit_zero_support_or_reorder_cells(self):
        self.mapping["bindings"]=self.expected[1:];self.save()
        with self.assertRaisesRegex(ValueError,"source-cell roster"):checker.verify(self.stage)

    def test_saved_null_choice_cannot_be_promoted_by_prose(self):
        self.advice=self.advice.replace("selected rule: `Unavailable`","selected rule: `rule`");self.save()
        with self.assertRaisesRegex(ValueError,"chosen-policy"):checker.verify(self.stage)

    def test_publication_source_bytes_and_anonymous_locators_are_bound(self):
        path=self.stage/self.mapping["publications"][0]["source"];path.write_text(path.read_text()+"\n")
        with self.assertRaisesRegex(ValueError,"publication bytes"):checker.verify(self.stage)

    def test_escaped_markdown_and_html_nulls_remain_distinct(self):
        self.assertEqual(checker.markdown_cells("| policy | value |\n| --- | --- |\n| a\\|b | Unavailable |\n"),["a|b","Unavailable"])
        parser=checker.SavedHTML();parser.feed("<table><td>a&amp;b</td><td>0</td></table>")
        self.assertEqual(parser.rows,["a&b","0"])


if __name__=="__main__":unittest.main()
