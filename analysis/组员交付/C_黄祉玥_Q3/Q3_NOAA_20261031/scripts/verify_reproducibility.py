"""Compare saved analysis artifacts to one full deterministic rerun."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"analysis/q3/补充材料/reproducibility_check.json"


def snapshot():
    paths=sorted((ROOT/"analysis/q3").rglob("*"))+sorted((ROOT/"analysis/noaa_source_card").rglob("*"))
    return {str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file() and p!=DEST}


if __name__=="__main__":
    subprocess.run([sys.executable,str(ROOT/"scripts/build_integrated.py"),"--check"],cwd=ROOT,check=True)
    before=snapshot()
    subprocess.run([sys.executable,str(ROOT/"scripts/run_q3.py")],cwd=ROOT,check=True)
    after=snapshot()
    changed=[p for p in sorted(set(before)|set(after)) if before.get(p)!=after.get(p)]
    result={"passed":not changed,"compared_artifacts":len(after),"changed_files":changed,"sha256":after}
    DEST.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="sha256"},ensure_ascii=False,indent=2))
    if changed:raise SystemExit(1)
