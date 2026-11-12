"""Commit verified remote data receipts to the requested branch after upload."""
from pathlib import Path
import json,subprocess,time

ROOT=Path('/home/lzz/ht_quality_github_20261112')
PROJECT=Path('/home/lzz/HT_Explo_quality_20261111')
BRANCH='sim/ht-height-quality-20261111'

def validate(data):
    if data.get('status')!='complete_verified' or len(data.get('releases',[]))!=2:
        raise RuntimeError('Full remote verification has not completed')
    if {r.get('tag') for r in data['releases']}!={'ht-quality-300s-20261111','ht-quality-600s-20261112'}:
        raise RuntimeError('Both distinct experiment receipts are required')
    for release in data['releases']:
        assets=release['verified_assets']
        if release['status']!='complete_verified' or len(assets)!=release['expected_assets'] or len({a['name'] for a in assets})!=len(assets):
            raise RuntimeError('Incomplete or duplicated remote asset receipts')
        if any(not a['size_and_sha256_verified'] or a['remote_digest']!='sha256:'+a['sha256'] for a in assets):
            raise RuntimeError('A remote digest was not verified')

def git(*args,check=True):
    return subprocess.run(['git','-C',str(PROJECT),*args],capture_output=True,text=True,check=check,timeout=180)

def main():
    data=json.loads((ROOT/'REMOTE_VERIFIED.json').read_text());validate(data)
    if git('branch','--show-current').stdout.strip()!=BRANCH:raise RuntimeError('Current worktree branch changed; receipts retained locally')
    if git('diff','--cached','--quiet',check=False).returncode:raise RuntimeError('Existing staged work is preserved; automatic receipt commit stopped')
    targets=[]
    for release in data['releases']:
        folder='ht_height_quality_20261111' if '300s' in release['tag'] else 'ht_height_quality_600s_20261112'
        doc=PROJECT/'docs/results'/folder
        paths=[doc/'UPLOAD.md',doc/'UPLOAD_STATUS.json',doc/'publication/REMOTE_RECEIPT.json']
        if git('diff','--quiet','--',*(str(p.relative_to(PROJECT)) for p in paths),check=False).returncode:
            raise RuntimeError('Uncommitted publication-page changes preserved; receipt files remain local')
        status=json.loads((doc/'UPLOAD_STATUS.json').read_text())
        status.update(raw_data_upload_status='complete_verified',complete_raw_data_remote_backup_verified=True,
            release_url=release['release_url'],verified_release_assets=len(release['verified_assets']),
            verified_wall_time=release['verified_wall_time'],remote_receipt='publication/REMOTE_RECEIPT.json')
        (doc/'UPLOAD_STATUS.json').write_text(json.dumps(status,indent=2))
        (doc/'publication/REMOTE_RECEIPT.json').write_text(json.dumps(release,indent=2))
        video=status['video_file_in_branch']
        (doc/'UPLOAD.md').write_text(f'**完整实验数据已上传并核验｜2026-11-12**\n\n代码、报告、图表和[轨迹视频]({video})保存在 `{BRANCH}`。对应代码/报告提交 `{release["target_commit"]}`。\n\n[完整实验数据附件]({release["release_url"]})：{len(release["verified_assets"])}个必需附件均已核对远端大小及GitHub SHA256。[远端逐附件回执](publication/REMOTE_RECEIPT.json)、[附件还原清单](publication/MANIFEST.json)、[原始文件SHA256](publication/FILES_SHA256.json)。\n\n中断/失败记录按原字节保留，不标作完整成功实验；如存在以incomplete开头的传输残留，它们不属于MANIFEST中的必需附件。原始本机数据全部保留，未清理。此页是最新上传状态，原始测量报告中的旧上传状态作为历史保留。还原说明见仓库 `tools/ht_quality_upload_20261112/README.md`。\n')
        targets.extend(paths)
    git('add','--sparse','--',*(str(p.relative_to(PROJECT)) for p in targets))
    if git('diff','--cached','--quiet',check=False).returncode:
        git('commit','-m','Verify full GitHub backups for HT quality experiments')
    git('push','origin',BRANCH)
    commit=git('rev-parse','HEAD').stdout.strip();remote=git('ls-remote','origin','refs/heads/'+BRANCH).stdout.split()[0]
    if commit!=remote:raise RuntimeError('Branch receipt push could not be confirmed')
    record={'status':'complete_verified','branch':BRANCH,'receipt_commit':commit,
        'releases':[x['release_url'] for x in data['releases']],'confirmed_wall_time':time.time()}
    (ROOT/'BRANCH_PUBLICATION.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2),flush=True)

if __name__=='__main__':main()
