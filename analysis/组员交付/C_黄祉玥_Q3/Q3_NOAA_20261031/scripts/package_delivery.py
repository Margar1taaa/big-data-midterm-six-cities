"""Package this task's reviewable deliverables, omitting runtime/cache/source archive."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"Q3_NOAA_20261031_交付包.zip"


if __name__=="__main__":
    verification=json.loads((ROOT/"analysis/q3/补充材料/verification.json").read_text(encoding="utf-8"))
    reproducibility=json.loads((ROOT/"analysis/q3/补充材料/reproducibility_check.json").read_text(encoding="utf-8"))
    if not verification["passed"] or not reproducibility["passed"]:
        raise SystemExit("Verification must pass before packaging.")
    paths=[ROOT/n for n in ["README.md","requirements.txt","requirements-lock.txt"]]
    for folder in ["scripts","docs","data","analysis"]:
        paths.extend(p for p in (ROOT/folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix!=".pyc")
    paths=sorted(paths,key=lambda p:p.relative_to(ROOT).as_posix())
    listing={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    checklist=ROOT/"交付文件清单.json"
    checklist.write_text(json.dumps({"files":len(listing),"sha256":listing},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with zipfile.ZipFile(DEST,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for p in [*paths,checklist]:
            info=zipfile.ZipInfo("Q3_NOAA_20261031/"+p.relative_to(ROOT).as_posix(),date_time=(2026,10,31,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,p.read_bytes())
    with zipfile.ZipFile(DEST) as archive:
        assert archive.testzip() is None,"zip integrity check failed"
        assert len(archive.namelist())==len(paths)+1
    print(json.dumps({"archive":str(DEST),"files":len(paths)+1,"bytes":DEST.stat().st_size,
                      "sha256":hashlib.sha256(DEST.read_bytes()).hexdigest()},ensure_ascii=False,indent=2))
