"""Partial scene evidence must survive export/publication without invented durations."""
import hashlib
import csv
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'scripts'))
import finalize_tare_multiscene as finalizer
import run_ht_multiscene as runner
import plot_tare_route_comparison as comparisons
import finalize_tare_multiscene_publication as publisher
import prune_published_ht_raw as retention


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def state():
    return dict(state='RUNNING',git_head='frozen',duration_s=600,runs=[
        dict(scenario='garage',state='FAILED',elapsed_measurement_s=569.5,error='interrupted'),
        dict(scenario='forest',state='PENDING'),dict(scenario='tunnel',state='PENDING')])


def complete_trial(suite,scene='garage'):
    trial=suite/scene
    write(trial/'manifest.json',dict(git_head='frozen'))
    write(trial/'COMPLETED.json',{})
    write(trial/'summary.json',dict(duration_s=600))
    write(trial/'suite_validation.json',dict(checks=dict(timer_completed=True,video_duration_matches=True)))


class InterruptedEvidenceTests(unittest.TestCase):
    def test_progress_does_not_become_measured_duration(self):
        with TemporaryDirectory() as directory:
            suite=Path(directory);s=state();before=json.dumps(s,sort_keys=True)
            proof=finalizer.collection_evidence(suite,s)
            self.assertEqual(proof['derived_state'],'INTERRUPTED_OR_UNFINALIZED')
            self.assertIsNone(proof['runs'][0]['measured_duration_s'])
            self.assertEqual(proof['runs'][0]['last_reported_progress_s'],569.5)
            self.assertFalse(any(r['validated_recording'] for r in proof['runs']))
            self.assertEqual(json.dumps(s,sort_keys=True),before)

    def test_export_entirely_partial_batch_keeps_source_and_unknowns(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);suite=root/'raw';archive=root/'selected';s=state()
            write(suite/'suite.json',s);write(suite/'garage/FAILURE.json',dict(error='capture interrupted'))
            original=(suite/'suite.json').read_bytes()
            job=root/'job.json';write(job,dict(archive=str(archive),candidate_commit='frozen'))
            with patch.object(finalizer,'ROOT',root),patch.object(sys,'argv',['finalize',str(suite),'--state',str(job),'--allow-interrupted']):
                finalizer.main()
            self.assertEqual((suite/'suite.json').read_bytes(),original)
            self.assertEqual((archive/'suite.json').read_bytes(),original)
            self.assertTrue((archive/'garage/FAILURE.json').is_file())
            self.assertFalse((suite/'forest').exists())
            self.assertFalse((suite/'tunnel').exists())
            text=(archive/'REPORT.md').read_text()
            self.assertIn('| garage | FAILED | 未知 | 569.5 | False |',text)
            self.assertIn('| forest | PENDING | 未知 | 未采到 | False |',text)
            self.assertFalse(list(archive.rglob('*.mp4')))
            self.assertTrue((archive/'multiscene_diagnostics.png').is_file())
            hashes=json.loads((archive/'files_sha256.json').read_text())
            for name,value in hashes.items():self.assertEqual(hashlib.sha256((archive/name).read_bytes()).hexdigest(),value)

    def test_unfinalized_suite_requires_explicit_interrupted_export(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);suite=root/'raw';write(suite/'suite.json',state())
            job=root/'job.json';write(job,dict(archive=str(root/'out'),candidate_commit='frozen'))
            with patch.object(sys,'argv',['finalize',str(suite),'--state',str(job)]):
                with self.assertRaisesRegex(ValueError,'Unfinalized suite'):finalizer.main()
            self.assertFalse((root/'out').exists())

    def test_active_evidence_writer_blocks_export_even_with_override(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);suite=root/'raw';write(suite/'suite.json',state())
            job=root/'job.json';write(job,dict(archive=str(root/'out'),candidate_commit='frozen'))
            with patch.object(finalizer,'active_evidence_workers',return_value=[123]),patch.object(sys,'argv',['finalize',str(suite),'--state',str(job),'--allow-interrupted']):
                with self.assertRaisesRegex(ValueError,'writers are still active'):finalizer.main()
            self.assertFalse((root/'out').exists())

    def test_validated_subset_uses_explicit_subset_export(self):
        with TemporaryDirectory() as directory:
            suite=Path(directory)/'raw';out=Path(directory)/'out';s=state()
            s['runs'][0].update(state='RECORDED',video_ok=True)
            write(suite/'suite.json',s);complete_trial(suite)
            proof=finalizer.collection_evidence(suite,s)
            def export(args):
                self.assertIn('--completed-subset',args)
                self.assertEqual(args[args.index('--scenarios')+1:],['garage'])
                out.mkdir();write(out/'suite.json',dict(state='RECORDED_SUBSET'))
                return type('Result',(),dict(returncode=0))()
            with patch.object(finalizer.subprocess,'run',side_effect=export):finalizer.export_available(suite,out,s,proof)
            self.assertEqual(json.loads((out/'suite.json').read_text())['state'],'RUNNING')
            self.assertEqual(json.loads((out/'validated_subset_suite.json').read_text())['state'],'RECORDED_SUBSET')

    def test_publication_counts_actual_validated_scenes(self):
        with TemporaryDirectory() as directory:
            suite=Path(directory);s=state();s['runs'].insert(0,dict(scenario='campus',state='RECORDED',video_ok=True))
            complete_trial(suite,'campus')
            rows,issues,overview,complete=publisher.publication_overview(suite,s)
            self.assertFalse(complete)
            self.assertIn('已获得1组',overview)
            self.assertIn('| garage | FAILED | 未知 | 569.5 |',rows[1])
            self.assertIn('forest:未获得完整且通过检查的记录',issues)
            self.assertNotIn('各记录600秒',overview)

    def test_handled_interrupt_writes_terminal_state_without_touching_pending(self):
        with TemporaryDirectory() as directory:
            suite=Path(directory);s=state()
            runner.finish_suite(suite,s,SystemExit(143))
            result=json.loads((suite/'FINISHED.json').read_text())
            self.assertEqual(result['state'],'INTERRUPTED')
            self.assertEqual(result['interruption'],dict(type='SystemExit',message='143'))
            self.assertEqual(result['runs'][1]['state'],'PENDING')
            self.assertNotIn('COMPLETED',(suite/'REPORT.md').read_text())


class ComparisonTests(unittest.TestCase):
    def test_fourth_historical_run_is_actually_plotted(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);args=['compare'];labels={f'candidate{i}' for i in range(4)}
            for i,label in enumerate(sorted(labels)):
                trial=root/label;trial.mkdir()
                for name,headers,data in [
                    ('observation_volume.csv',['time_s','observed_free_volume_m3'],[(t,1+t*(i+1)) for t in range(0,601,10)]),
                    ('timeseries.csv',['t_s','distance_m','odom_speed_mps','x_m','y_m'],[(t,t*.1,.1,t*.1,i) for t in range(0,601,10)])]:
                    with (trial/name).open('w') as stream:
                        writer=csv.writer(stream);writer.writerow(headers);writer.writerows(data)
                write(trial/'summary.json',dict(distance_m=60))
                write(trial/'endurance_audit.json',dict(external_metrics=dict(fully_stopped_fraction=.1,stationary_turn_fraction=.1,reverse_command_fraction=0),sampled_map_age_s={}))
                args+=['--run',label+'='+str(trial)]
            args+=['--output',str(root/'plots')]
            seen=set();original=comparisons.plt.Axes.plot
            def observe(axis,*values,**kwargs):
                if 'label' in kwargs:seen.add(kwargs['label'])
                return original(axis,*values,**kwargs)
            with patch.object(sys,'argv',args),patch.object(comparisons.plt.Axes,'plot',new=observe):comparisons.main()
            self.assertEqual(seen,labels)
            self.assertTrue((root/'plots/tare_architecture_comparison.png').is_file())


class RetentionTests(unittest.TestCase):
    def modern(self,tag,status='COMPLETE_VALIDATED_COLLECTION'):
        return dict(tag=tag,publication_status=status,verified_at='test',collection_validation=dict(garage=dict(
            complete600s=status=='COMPLETE_VALIDATED_COLLECTION',recorded_state='RECORDED',checks=dict(timer_completed=True))))

    def test_partial_receipt_cannot_displace_two_complete_suites(self):
        rows=[(44,None,dict(tag='unknown')),(43,None,self.modern('stage43')),
              (42,None,self.modern('partial42','RETAINED_FAILURES_NOT_A_VALIDATED_COMPLETE_SUITE')),
              (41,None,self.modern('stage41')),(40,None,self.modern('stage40'))]
        protected,incomplete=retention.retention_protection(rows,2)
        self.assertEqual(protected,{'unknown','stage43','partial42','stage41'})
        self.assertEqual(incomplete,{'unknown','partial42'})

    def test_legacy_complete_receipt_uses_retained_evidence(self):
        with TemporaryDirectory() as directory:
            archive=Path(directory);s=dict(git_head='frozen',state='COMPLETED',duration_s=600,runs=[dict(scenario='garage',state='RECORDED',checks=dict(ok=True))])
            write(archive/'suite.json',s);write(archive/'FINISHED.json',s);complete_trial(archive)
            receipt=dict(tag='legacy41',tested_commit='frozen',result_archive=str(archive))
            self.assertTrue(retention.complete_collection(receipt))
            (archive/'garage/summary.json').unlink()
            self.assertFalse(retention.complete_collection(receipt))


if __name__=='__main__':unittest.main()
