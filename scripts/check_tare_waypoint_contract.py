#!/usr/bin/env python3
"""Read-only upstream-body and routing-contract checks; no adjacent workspace needed."""
from pathlib import Path
import re,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'docs/fixes/evidence/2026-10-20_tare_waypoint'
def body(source,name):
    m=re.search(r'\b'+re.escape(name)+r'\s*\(',source);assert m,name
    start=source.index('{',m.end());depth=0
    for token in re.finditer(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]',source[start:]):
        if token.group()=='{':depth+=1
        elif token.group()=='}':
            depth-=1
            if depth==0:return source[start:start+token.end()]
    raise ValueError(name)
def main():
    results=[]
    for row in json.loads((EVIDENCE/'upstream_functions.json').read_text()):
        source=ROOT/'src/tare_planner'/Path(row['reference']).parent/'tare_original.cpp'
        actual=hashlib.sha256(body(source.read_text(),row['restored']).encode()).hexdigest()
        reference=hashlib.sha256(body((EVIDENCE/(row['method']+'.cpp.txt')).read_text(),row['method']).encode()).hexdigest()
        assert actual==reference==row['body_sha256'],row['method']
        results.append({'method':row['method'],'body_sha256':actual,'upstream_body_equal':True})
    # Original coverage still compares the complete route length and iterates
    # kLocalPathOptimizationItrMax; the HT single-target objective stays legacy.
    local=(ROOT/'src/tare_planner/src/local_coverage_planner/tare_original.cpp').read_text()
    coverage=body(local,'SolveTareCoverageProblem')
    assert 'parameters_.kLocalPathOptimizationItrMax' in coverage
    assert 'ht_last_cost_' not in coverage and 'SolveHTTSP' not in coverage
    print(json.dumps({'passed':True,'reference_commit':'b6760adb4280b379567c76f4e684ce628e28ef71','functions':results},indent=2))
if __name__=='__main__':main()
