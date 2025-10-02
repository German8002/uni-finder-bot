from pathlib import Path
from importlib import import_module
from typing import Dict, Any, List
import os, json

ROOT = Path(__file__).resolve().parents[1]
SOURCES_DIR = ROOT / "scripts" / "sources"
OUT_DIR = ROOT / "public" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

REFRESH = os.getenv("SCRAPER_REFRESH_CACHE", "false").lower() == "true"
ONLY_SOURCE = os.getenv("ONLY_SOURCE", "").strip()

def _load_adapters():
    adapters = []
    for p in SOURCES_DIR.glob("*.py"):
        if p.name == "__init__.py":
            continue
        if ONLY_SOURCE and p.stem != ONLY_SOURCE:
            continue
        mod = import_module(f"scripts.sources.{p.stem}")
        if hasattr(mod, "fetch"):
            adapters.append(mod)
    if not adapters:
        raise SystemExit("No adapters found in scripts/sources")
    return adapters

def _norm_program(p: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "university": p.get("university") or p.get("uni") or p.get("ВУЗ"),
        "city": p.get("city") or p.get("город"),
        "program": p.get("program") or p.get("profile") or p.get("direction"),
        "level": p.get("level") or p.get("уровень"),
        "form": p.get("form") or p.get("форма"),
        "cost": p.get("cost") or p.get("стоимость"),
        "min_score": p.get("min_score") or p.get("минимальные баллы"),
        "source": p.get("source"),
        "url": p.get("url"),
    }

def _norm_uni(u: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": u.get("name") or u.get("university") or u.get("ВУЗ"),
        "city": u.get("city") or u.get("город"),
        "site": u.get("site") or u.get("сайт"),
        "source": u.get("source"),
        "url": u.get("url"),
    }

def main():
    programs: List[Dict[str, Any]] = []
    universities: List[Dict[str, Any]] = []

    for adapter in _load_adapters():
        print(f"[build] run {adapter.__name__} refresh={REFRESH}")
        out = adapter.fetch(refresh=REFRESH)
        programs += [_norm_program(p) for p in out.get("programs", [])]
        universities += [_norm_uni(u) for u in out.get("universities", [])]

    def k_prog(p):
        return (str(p.get("university")).lower().strip(),
                str(p.get("program")).lower().strip(),
                str(p.get("level")).lower().strip(),
                str(p.get("form")).lower().strip(),
                str(p.get("city")).lower().strip())
    def k_uni(u):
        return (str(u.get("name")).lower().strip(), str(u.get("city")).lower().strip())

    seen=set(); uniq=[]
    for p in programs:
        kp=k_prog(p)
        if kp in seen: continue
        seen.add(kp); uniq.append(p)

    seenu=set(); uniqq=[]
    for u in universities:
        ku=k_uni(u)
        if ku in seenu: continue
        seenu.add(ku); uniqq.append(u)

    (OUT_DIR/"programs.json").write_text(json.dumps(uniq, ensure_ascii=False, indent=2), "utf-8")
    (OUT_DIR/"universities.json").write_text(json.dumps(uniqq, ensure_ascii=False, indent=2), "utf-8")
    print(f"[build] programs={len(uniq)} universities={len(uniqq)}")

if __name__ == "__main__":
    main()
