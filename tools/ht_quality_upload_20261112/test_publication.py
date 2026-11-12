"""Check original-byte restore and strict server digest verification offline."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys,tarfile,tempfile,unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('upload',HERE/'upload.py');upload=importlib.util.module_from_spec(spec);spec.loader.exec_module(upload)
spec=importlib.util.spec_from_file_location('receipts',HERE/'publish_receipts.py');receipts=importlib.util.module_from_spec(spec);spec.loader.exec_module(receipts)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class PublicationTests(unittest.TestCase):
    def test_superseded_full_upload_never_calls_github(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'PLAN.json').write_text(json.dumps({'upload_enabled':False}))
            with patch.object(upload,'ROOT',root),patch.object(upload,'api',side_effect=AssertionError('API must not be called')):
                with self.assertRaisesRegex(RuntimeError,'superseded'):upload.main()

    def test_incomplete_remote_backup_cannot_be_marked_complete(self):
        with self.assertRaises(RuntimeError):receipts.validate({'status':'uploading','releases':[]})
        asset={'name':'part.mcap','sha256':'a'*64,'remote_digest':'sha256:'+'a'*64,'size_and_sha256_verified':True}
        release={'tag':'ht-quality-300s-20261111','status':'complete_verified','verified_assets':[asset],'expected_assets':1}
        second=dict(release,tag='ht-quality-600s-20261112')
        receipts.validate({'status':'complete_verified','releases':[release,second]})
        incomplete=dict(second,expected_assets=2)
        with self.assertRaises(RuntimeError):receipts.validate({'status':'complete_verified','releases':[release,incomplete]})
        with self.assertRaises(RuntimeError):receipts.validate({'status':'complete_verified','releases':[release,release]})

    def test_same_size_is_not_integrity_and_starter_is_not_complete(self):
        expected={'bytes':4,'sha256':'a'*64};remote={'state':'uploaded','size':4,'digest':'sha256:'+'a'*64}
        self.assertTrue(upload.matches(remote,expected))
        for modified in [dict(remote,digest='sha256:'+'b'*64),dict(remote,digest=None),dict(remote,state='starter'),dict(remote,size=3)]:
            self.assertFalse(upload.matches(modified,expected))

    def fixture(self,root):
        assets=root/'downloads';assets.mkdir();source=root/'source';source.mkdir()
        bag=assets/'renamed-original.mcap';bag.write_bytes(b'MCAP\0\x01original bytes\0\xff')
        # Preserve the interrupted raw CSV's embedded NUL byte exactly.
        evidence=source/'metrics.csv';evidence.write_bytes(b'elapsed,distance\n339.25,15.7\n\0')
        inventory=[{'path':'trial/runs/bag/bag_0.mcap','bytes':bag.stat().st_size,'sha256':sha(bag)},
                   {'path':'trial/runs/metrics.csv','bytes':evidence.stat().st_size,'sha256':sha(evidence)}]
        files=source/'FILES_SHA256.json';files.write_text(json.dumps(inventory));archive=assets/'evidence.tar.gz'
        with tarfile.open(archive,'w:gz') as tar:
            tar.add(evidence,arcname='trial/runs/metrics.csv');tar.add(files,arcname='FILES_SHA256.json')
        manifest={'assets':[{'name':bag.name,'kind':'original_mcap','restore_path':inventory[0]['path'],'bytes':bag.stat().st_size,'sha256':sha(bag)},
                            {'name':archive.name,'kind':'evidence_archive','bytes':archive.stat().st_size,'sha256':sha(archive)}]}
        path=assets/'MANIFEST.json';path.write_text(json.dumps(manifest));return assets,path,bag,evidence

    def test_restore_preserves_raw_names_nulls_and_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);assets,manifest,bag,evidence=self.fixture(root);out=root/'restored'
            subprocess.run([sys.executable,str(HERE/'restore.py'),'--manifest',str(manifest),'--assets-dir',str(assets),'--output',str(out)],check=True,capture_output=True)
            self.assertEqual((out/'trial/runs/bag/bag_0.mcap').read_bytes(),bag.read_bytes())
            self.assertEqual((out/'trial/runs/metrics.csv').read_bytes(),evidence.read_bytes())

    def test_corrupt_download_rejected_before_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);assets,manifest,bag,_=self.fixture(root);out=root/'restored'
            original=bag.read_bytes();bag.write_bytes(bytes([original[0]^1])+original[1:])
            result=subprocess.run([sys.executable,str(HERE/'restore.py'),'--manifest',str(manifest),'--assets-dir',str(assets),'--output',str(out)],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()
