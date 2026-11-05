import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import pandas as pd
import requests

from scripts import refresh_report as refresh


class RefreshReviewTests(unittest.TestCase):
    def application(self, year=2025, value=7):
        return {"Year":year,"Country of asylum (ISO)":"GBR","Country of asylum":"United Kingdom",
                "Country of origin (ISO)":"AFG","Country of origin":"Afghanistan","Cases / Persons":"P","applied":value}

    def test_missing_is_not_reported_zero(self):
        old = pd.DataFrame([self.application(2024,2)])
        new = pd.DataFrame([self.application(2024,2),self.application(2025,0)])
        changes = refresh.compare(old,new,["applied"])
        self.assertEqual(changes.Year.tolist(),[2025])
        self.assertTrue(pd.isna(changes.applied_accepted.iloc[0]))
        self.assertEqual(changes.applied_candidate.iloc[0],0)

    def test_reordering_and_splitting_source_rows_does_not_create_revisions(self):
        old = pd.DataFrame([self.application(2024,10),self.application(2025,4)])
        new = pd.DataFrame([self.application(2025,4),self.application(2024,3),self.application(2024,7)])
        self.assertTrue(refresh.compare(old,new,["applied"]).empty)

    def test_unreconciled_decisions_do_not_get_a_protection_rate(self):
        apps = pd.DataFrame([self.application()])
        row = self.application()
        row.update(dict(zip(refresh.OUTCOMES,[3,2,4,1,11])))
        records = refresh.country_rows(apps,pd.DataFrame([row]))
        self.assertIsNone(records[0]['protection_rate'])
        self.assertIsNone(records[0]['closed_share'])
        self.assertEqual(records[0]['decisions'],11)

    def test_download_failure_leaves_accepted_edition_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); site=root/'quarto-preview'; (site/'data').mkdir(parents=True)
            apps=pd.DataFrame([self.application()])
            decision=self.application(); decision.update(dict(zip(refresh.OUTCOMES,[3,2,4,1,10])))
            apps.to_csv(root/'asylum-applications.csv',index=False)
            pd.DataFrame([decision]).to_csv(root/'asylum-decisions.csv',index=False)
            hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('*.csv')}
            (site/'_inputs.json').write_text(json.dumps({'inputs':hashes}))
            (site/'data/explorer.json').write_text('{}')
            (site/'index.qmd').write_text('Accepted report')
            (root/'UNHCRData.ipynb').write_text('User notebook')
            before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
            output=root/'review'
            with patch.object(refresh,'ROOT',root),patch.object(refresh,'SITE',site),patch.object(refresh.explorer,'refresh',side_effect=requests.ConnectionError('offline')):
                with self.assertRaises(requests.ConnectionError):
                    refresh.run(output=output)
            for path,content in before.items():
                self.assertEqual(path.read_bytes(),content)
            self.assertTrue((output/'FAILED.json').exists())
            self.assertFalse((output/'READY.txt').exists())
            self.assertFalse((output/'index.html').exists())

    def test_existing_review_run_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            sentinel=Path(temp)/'index.html';sentinel.write_text('Previous review')
            with self.assertRaises(ValueError):
                refresh.run(output=temp)
            self.assertEqual(sentinel.read_text(),'Previous review')

    def test_country_renaming_does_not_split_top20_volume(self):
        first = self.application(2024,4)
        second = self.application(2025,7); second['Country of asylum']='United Kingdom renamed'
        ranked = refresh.ranking(pd.DataFrame([first,second]),'Country of asylum (ISO)','Country of asylum')
        self.assertEqual(len(ranked),1)
        self.assertEqual(ranked.Applications.iloc[0],11)
        self.assertEqual(ranked['Country of asylum'].iloc[0],'United Kingdom renamed')

    def test_new_application_year_is_flagged_before_decisions_catch_up(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); site=root/'quarto-preview'; (site/'data').mkdir(parents=True)
            apps=pd.DataFrame([self.application(2024)])
            decision=self.application(2024); decision.update(dict(zip(refresh.OUTCOMES,[3,2,4,1,10])))
            decs=pd.DataFrame([decision])
            for filename,frame in [('asylum-applications.csv',apps),('asylum-decisions.csv',decs)]:
                frame.to_csv(root/filename,index=False)
            hashes={p.name:refresh.sha(p) for p in root.glob('*.csv')}
            (site/'_inputs.json').write_text(json.dumps({'inputs':hashes}))
            (site/'data/explorer.json').write_text('{}')
            stock={'response':{'items':[{'year':2024,'asylum_seekers':100}]}}
            (site/'data/pending-stock-series.json').write_text(json.dumps(stock))
            candidate_apps=pd.concat([apps,pd.DataFrame([self.application(2025,9)])])
            def download(bundled=False):
                dest=refresh.explorer.DEST
                with ZipFile(dest/'source-snapshot.zip','w') as z:
                    z.writestr('asylum-applications.csv',candidate_apps.to_csv(index=False))
                    z.writestr('asylum-decisions.csv',decs.to_csv(index=False))
                metadata={'sources':{},'downloaded_at_utc':'2026-11-05T00:00:00Z','outcome_total_mismatch_rows':0}
                (dest/'explorer.json').write_text(json.dumps({'metadata':metadata}))
            with patch.object(refresh,'ROOT',root),patch.object(refresh,'SITE',site),patch.object(refresh.explorer,'refresh',side_effect=download),patch.object(refresh,'stock_snapshot',return_value=stock),patch.object(refresh,'render_review'):
                result=refresh.run(output=root/'review')
            audit=json.loads((result/'audit.json').read_text())
            self.assertEqual(audit['candidate_common_year'],2024)
            self.assertEqual(audit['new_years'],[2025])
            self.assertEqual(audit['status'],'NEW YEARS — EDITION MIGRATION REQUIRED')
            self.assertFalse(audit['authored_report_rebuilt'])


if __name__ == '__main__':
    unittest.main()
