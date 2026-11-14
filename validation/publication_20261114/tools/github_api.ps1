param([string]$Action='probe',[string]$PlanPath='D:\HT-Execution-300s\github_publish_20261114\PLAN.json',[string]$AssetName='')
$ErrorActionPreference='Stop'
$repoPath='C:\Users\李哲舟\Desktop\python code\work\ht_execution_fixes'
$env:GIT_TERMINAL_PROMPT='0';$env:GCM_INTERACTIVE='Never'
$psi=[Diagnostics.ProcessStartInfo]::new();$psi.FileName=(Get-Command git).Source;$psi.WorkingDirectory=$repoPath;$psi.UseShellExecute=$false;$psi.RedirectStandardInput=$true;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true
$psi.ArgumentList.Add('credential');$psi.ArgumentList.Add('fill')
$proc=[Diagnostics.Process]::Start($psi)
$proc.StandardInput.WriteLine('protocol=https');$proc.StandardInput.WriteLine('host=github.com');$proc.StandardInput.WriteLine();$proc.StandardInput.Close()
$credentialText=$proc.StandardOutput.ReadToEnd();$credentialError=$proc.StandardError.ReadToEnd();$proc.WaitForExit()
if($proc.ExitCode -ne 0){throw 'Git credential manager could not supply GitHub credentials noninteractively.'}
$credential=@{};foreach($line in ($credentialText -split '[\r\n]+')){if($line.Contains('=')){$parts=$line.Split('=',2);$credential[$parts[0]]=$parts[1]}}
if(-not $credential['password']){throw 'No GitHub credential returned.'}
$handler=[Net.Http.HttpClientHandler]::new();$handler.Proxy=[Net.WebProxy]::new('http://127.0.0.1:7890');$handler.UseProxy=$true
$client=[Net.Http.HttpClient]::new($handler);$client.Timeout=[TimeSpan]::FromMinutes(20)
$client.DefaultRequestHeaders.UserAgent.ParseAdd('HT-Explo-publication/1.0')
$client.DefaultRequestHeaders.Authorization=[Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer',$credential['password'])
$client.DefaultRequestHeaders.Add('X-GitHub-Api-Version','2022-11-28')
$credential.Clear();$credentialText=$null;$credentialError=$null
function Call-GitHub([string]$Method,[string]$Url,$Body=$null){
 $req=[Net.Http.HttpRequestMessage]::new([Net.Http.HttpMethod]::new($Method),$Url)
 $req.Headers.Accept.ParseAdd('application/vnd.github+json')
 if($null -ne $Body){$json=$Body|ConvertTo-Json -Depth 40 -Compress;$req.Content=[Net.Http.ByteArrayContent]::new([Text.Encoding]::UTF8.GetBytes($json));$req.Content.Headers.ContentType=[Net.Http.Headers.MediaTypeHeaderValue]::new('application/json')}
 $res=$client.SendAsync($req).GetAwaiter().GetResult();$raw=$res.Content.ReadAsStringAsync().GetAwaiter().GetResult()
 if(-not $res.IsSuccessStatusCode){$message=try{($raw|ConvertFrom-Json).message}catch{'request rejected'};throw "GitHub $Method failed: $([int]$res.StatusCode) $message"}
 $value=if($raw){$raw|ConvertFrom-Json -AsHashtable}else{$null};$res.Dispose();$req.Dispose();return $value
}
try {
 if($Action -eq 'probe'){
  $user=Call-GitHub 'GET' 'https://api.github.com/user'
  $repo=Call-GitHub 'GET' 'https://api.github.com/repos/CQULzz/HT_Explo'
  [ordered]@{login=$user.login;repository=$repo.full_name;push_permission=$repo.permissions.push;default_branch=$repo.default_branch}|ConvertTo-Json
 } else {
  $plan=Get-Content -LiteralPath $PlanPath -Raw | ConvertFrom-Json -AsHashtable
  $base='https://api.github.com/repos/CQULzz/HT_Explo'
  $statePath=Join-Path (Split-Path $PlanPath) 'RELEASE_STATE.json'
  $receiptPath=Join-Path (Split-Path $PlanPath) 'REMOTE_RECEIPTS.json'
  if($Action -eq 'create'){
   $all=Call-GitHub 'GET' "$base/releases?per_page=100"
   $matching=@($all | Where-Object {$_.tag_name -eq $plan.tag})
   if($matching.Count -gt 1){throw 'Multiple matching releases.'}
   if($matching.Count -eq 1){$release=$matching[0]}else{
    $release=Call-GitHub 'POST' "$base/releases" @{
     tag_name=$plan.tag;target_commitish=$plan.commit;name=$plan.title
     body=(Get-Content -LiteralPath $plan.notes_path -Raw)
     draft=$true;prerelease=$true
    }
   }
   [ordered]@{id=$release.id;tag=$release.tag_name;html_url=$release.html_url;draft=$release.draft} | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8
   Write-Output "Release prepared: $($release.id), draft=$($release.draft)"
  } elseif($Action -eq 'upload'){
   $state=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json -AsHashtable
   $entries=@($plan.assets|Where-Object {$_.name -eq $AssetName})
   if($entries.Count -ne 1){throw 'Select exactly one planned asset.'}
   $entry=$entries[0]
   $local=Get-Item -LiteralPath $entry.path
   $sha=(Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash.ToLowerInvariant()
   if($local.Length -ne $entry.bytes -or $sha -ne $entry.sha256){throw "Local asset changed: $AssetName"}
   $assets=Call-GitHub 'GET' "$base/releases/$($state.id)/assets?per_page=100"
   $existing=@($assets|Where-Object {$_.name -eq $entry.name})
   if($existing.Count){
    if($existing.Count -ne 1 -or $existing[0].size -ne $entry.bytes -or $existing[0].digest -ne "sha256:$sha"){
     throw "Conflicting existing asset: $AssetName; nothing overwritten."
    }
    Write-Output "Already uploaded and digest matched: $AssetName"
   }else{
    $url="https://uploads.github.com/repos/CQULzz/HT_Explo/releases/$($state.id)/assets?name=$([Uri]::EscapeDataString($entry.name))"
    $stream=[IO.File]::OpenRead($entry.path)
    $req=[Net.Http.HttpRequestMessage]::new([Net.Http.HttpMethod]::Post,$url)
    $req.Content=[Net.Http.StreamContent]::new($stream)
    $req.Content.Headers.ContentType=[Net.Http.Headers.MediaTypeHeaderValue]::new($entry.content_type)
    $req.Content.Headers.ContentLength=$local.Length
    try{
     $res=$client.SendAsync($req).GetAwaiter().GetResult()
     $raw=$res.Content.ReadAsStringAsync().GetAwaiter().GetResult()
     if(-not $res.IsSuccessStatusCode){throw "Asset upload failed: $([int]$res.StatusCode)"}
     $asset=$raw|ConvertFrom-Json -AsHashtable
     if($asset.size -ne $entry.bytes -or ($asset.digest -and $asset.digest -ne "sha256:$sha")){throw "Uploaded metadata mismatch: $AssetName"}
     Write-Output "Uploaded: $($asset.name), bytes=$($asset.size), digest=$($asset.digest)"
    }finally{
     if($res){$res.Dispose()};$req.Dispose();$stream.Dispose()
    }
   }
  } elseif($Action -eq 'verify'){
   $state=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json -AsHashtable
   $assets=Call-GitHub 'GET' "$base/releases/$($state.id)/assets?per_page=100"
   $receipts=@()
   foreach($entry in $plan.assets){
    $match=@($assets|Where-Object {$_.name -eq $entry.name})
    if($match.Count -ne 1){throw "Missing or duplicated asset: $($entry.name)"}
    $asset=$match[0]
    if($asset.size -ne $entry.bytes -or ($asset.digest -and $asset.digest -ne "sha256:$($entry.sha256)")){throw 'Remote metadata mismatch.'}
    # Re-download the remote asset via the authenticated asset API and hash bytes.
    $req=[Net.Http.HttpRequestMessage]::new([Net.Http.HttpMethod]::Get,$asset.url)
    $req.Headers.Accept.ParseAdd('application/octet-stream')
    try{
     $res=$client.SendAsync($req,[Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
     if(-not $res.IsSuccessStatusCode){throw "Remote download failed: $([int]$res.StatusCode)"}
     $stream=$res.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
     $digest=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($stream)).ToLowerInvariant()
     if($digest -ne $entry.sha256){throw "Downloaded SHA256 mismatch: $($entry.name)"}
     $receipts += [ordered]@{name=$asset.name;asset_id=$asset.id;bytes=$asset.size;sha256=$digest;github_digest=$asset.digest;url=$asset.browser_download_url;download_sha256_verified=$true}
     Write-Output "Remote bytes verified: $($entry.name)"
    }finally{if($stream){$stream.Dispose()};if($res){$res.Dispose()};$req.Dispose()}
   }
   [ordered]@{repository='CQULzz/HT_Explo';release_id=$state.id;tag=$plan.tag;target_commit=$plan.commit;verified_at_utc=[DateTime]::UtcNow.ToString('o');assets=$receipts} | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $receiptPath -Encoding utf8
  } elseif($Action -eq 'publish'){
   $state=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json -AsHashtable
   $receipt=Get-Content -LiteralPath $receiptPath -Raw|ConvertFrom-Json -AsHashtable
   if($receipt.release_id -ne $state.id -or $receipt.assets.Count -ne $plan.assets.Count){throw 'Complete verification receipts required.'}
   $release=Call-GitHub 'PATCH' "$base/releases/$($state.id)" @{draft=$false;prerelease=$true;make_latest='false'}
   if($release.draft){throw 'Release remained draft.'}
   $state.html_url=$release.html_url;$state.draft=$false
   $state|ConvertTo-Json|Set-Content -LiteralPath $statePath -Encoding utf8
   Write-Output "Published: $($release.html_url)"
  } elseif($Action -eq 'status'){
   $release=Call-GitHub 'GET' "$base/releases/tags/$($plan.tag)"
   [ordered]@{url=$release.html_url;draft=$release.draft;prerelease=$release.prerelease;tag=$release.tag_name;assets=@($release.assets|ForEach-Object {[ordered]@{name=$_.name;bytes=$_.size;digest=$_.digest}})}|ConvertTo-Json -Depth 8
  }else{throw "Unknown action: $Action"}
 }
} finally {$client.Dispose();$handler.Dispose();$proc.Dispose()}
