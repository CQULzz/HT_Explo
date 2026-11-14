$ErrorActionPreference='Stop'
$out='D:\HT-Execution-300s\github_publish_20261114'
$repo='C:\Users\李哲舟\Desktop\python code\work\ht_execution_fixes'
$publication=Join-Path $repo 'validation\publication_20261114'
$tag='ht-campus-pcd-600s-20261114'
$rows=@(
 @{name='indoor600s_rviz_4x.mp4';path='D:\HT-Execution-300s\rviz_video_20261114\rviz_exploration_full_4x.mp4';sha256='f90bbb6bb4ba86982b67fb05e7c92733494eb91aa8ebbd524f6d366df7771ae1'},
 @{name='indoor_recovery_1x.mp4';path='D:\HT-Execution-300s\rviz_video_20261114\rviz_recovery_detail_1x.mp4';sha256='f044ecec39229f250fbc8f23c54afb1043664d2286936469103b4c3e81bb1786'},
 @{name='campus600s_rviz_4x.mp4';path='D:\HT-Execution-300s\campus_pcd_videos_20261114\campus\rviz_exploration_full_4x.mp4';sha256='64043a4a114507f2617e2fbc5c90c3df71e8b51912f2d49716e3fb45fba275c5'},
 @{name='recordedpcd600s_rviz_4x.mp4';path='D:\HT-Execution-300s\campus_pcd_videos_20261114\user_pcd\rviz_exploration_full_4x.mp4';sha256='3e26ea74a5a437af6a3fbdc8853271aad6418af8f25668957c3b1aab989b57e9'},
 @{name='ht-execution-runtime-source-20261114.tar.gz';path=(Join-Path $out 'ht-execution-runtime-source-20261114.tar.gz');sha256='1450dd469dfddc5b8e2295f6d41194c607d8125758cc98e11b1dd719d4d6409d'},
 @{name='ht-execution-evidence-20261114.tar.gz';path=(Join-Path $out 'ht-execution-evidence-20261114.tar.gz');sha256='d2ced9fcc1fface480dfa184eacd030e26c8e78f8d7fd9ff69c97d080faeb04a'}
)
$assets=@()
foreach($row in $rows){
 $file=Get-Item -LiteralPath $row.path
 $sha=(Get-FileHash -LiteralPath $row.path -Algorithm SHA256).Hash.ToLowerInvariant()
 if($sha -ne $row.sha256){throw "Source checksum mismatch: $($row.name)"}
 $assets += [ordered]@{name=$row.name;path=$row.path;bytes=$file.Length;sha256=$sha;content_type=$(if($row.name.EndsWith('.mp4')){'video/mp4'}else{'application/gzip'})}
}
$sums=($assets | ForEach-Object {"$($_.sha256)  $($_.name)"}) -join "`n"
$sumPath=Join-Path $out 'SHA256SUMS.txt'
[IO.File]::WriteAllText($sumPath,$sums+"`n",[Text.UTF8Encoding]::new($false))
$assets += [ordered]@{name='SHA256SUMS.txt';path=$sumPath;bytes=(Get-Item $sumPath).Length;sha256=(Get-FileHash $sumPath -Algorithm SHA256).Hash.ToLowerInvariant();content_type='text/plain'}
$plan=[ordered]@{repository='CQULzz/HT_Explo';branch='fix/ht-execution-20261113';tag=$tag;commit='PENDING_PUBLICATION_COMMIT';title='HT execution fixes and indoor/campus/PCD experiments — 2026-11-14';notes_path=(Join-Path $out 'RELEASE_NOTES.md');assets=$assets}
$plan | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $out 'PLAN.json') -Encoding utf8
$publicAssets=@($assets|ForEach-Object {[ordered]@{name=$_.name;bytes=$_.bytes;sha256=$_.sha256;url="https://github.com/CQULzz/HT_Explo/releases/download/$tag/$($_.name)"}})
[ordered]@{repository=$plan.repository;branch=$plan.branch;release_tag=$tag;source_entries_verified=3443;tested_project_files_verified=176;assets=$publicAssets}|ConvertTo-Json -Depth 20|Set-Content -LiteralPath (Join-Path $publication 'ASSETS.json') -Encoding utf8
Copy-Item -LiteralPath (Join-Path $out 'SOURCE_MANIFEST.json') -Destination $publication
Copy-Item -LiteralPath $sumPath -Destination $publication
$toolDir=Join-Path $publication 'tools'
New-Item -ItemType Directory -Force -Path $toolDir | Out-Null
foreach($name in @('build_packages.py','github_api.ps1','prepare_publication.ps1')){
 Copy-Item -LiteralPath (Join-Path $out $name) -Destination $toolDir
}
Copy-Item -LiteralPath (Join-Path $out 'RELEASE_NOTES.md') -Destination $publication
$totalBytes=0L
foreach($entry in $assets){$totalBytes += $entry.bytes}
Write-Output "Prepared $($assets.Count) assets; $totalBytes bytes total."
