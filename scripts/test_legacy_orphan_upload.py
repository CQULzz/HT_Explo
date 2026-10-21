"""Never overwrite valid remote assets while recovering abandoned starters."""
import copy,datetime,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import archive_legacy_ht_data as archive


class OrphanUploadTest(unittest.TestCase):
    def asset(self):
        return dict(id=12,name='legacy-fixture.tar.zst.part006',state='starter',
                    size=512,digest=None,updated_at='2020-01-01T00:00:00Z')

    def test_stale_starter_is_preserved_outside_part_wildcard(self):
        original=self.asset();current=copy.deepcopy(original);calls=[]
        def gh(*args):
            calls.append(args)
            if 'PATCH' in args:
                current['name']=next(x[5:] for x in args if x.startswith('name='))
            return json.dumps(current)
        with tempfile.TemporaryDirectory() as directory,patch.object(archive,'OUT',Path(directory)),patch.object(archive,'gh',side_effect=gh),patch('psutil.process_iter',return_value=[]):
            self.assertTrue(archive.quarantine_incomplete_asset(original,'tag'))
            self.assertEqual(current['name'],'incomplete-upload-12.bin')
            self.assertEqual(current['size'],original['size'])
            self.assertEqual(current['state'],'starter')
            self.assertFalse(any('DELETE' in call for call in calls))
            journal=json.loads((Path(directory)/'quarantined_uploads.json').read_text())
            self.assertEqual(journal[0]['before']['name'],original['name'])

    def test_uploaded_conflict_is_never_renamed(self):
        asset=self.asset();asset.update(state='uploaded',digest='sha256:other')
        with patch.object(archive,'gh') as gh:
            self.assertFalse(archive.quarantine_incomplete_asset(asset,'tag'));gh.assert_not_called()

    def test_recent_unowned_upload_is_not_touched(self):
        asset=self.asset();asset['updated_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        with patch.object(archive,'gh') as gh:
            self.assertFalse(archive.quarantine_incomplete_asset(asset,'tag'));gh.assert_not_called()

    def test_active_owned_uploader_blocks_recovery(self):
        class Process:
            info=dict(name='gh',cmdline=['gh','release','upload','tag','/tmp/legacy-fixture.tar.zst.part006'])
        with patch.object(archive,'gh') as gh,patch('psutil.process_iter',return_value=[Process()]):
            with self.assertRaisesRegex(ValueError,'active owned uploader'):
                archive.quarantine_incomplete_asset(self.asset(),'tag')
            gh.assert_not_called()


if __name__=='__main__':unittest.main()
