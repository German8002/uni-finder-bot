from pathlib import Path
import json
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SCHEMAS = ROOT / "scripts" / "schemas"

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def check(json_path: Path, schema_path: Path, name: str):
    data = load(json_path)
    schema = load(schema_path)
    v = Draft202012Validator(schema)
    errors = sorted(v.iter_errors(data), key=lambda e: e.path)
    if errors:
        for e in errors:
            print(f"[schema] {name}: {e.message} at {list(e.path)}")
        raise SystemExit(f"{name} schema validation failed")
    print(f"[schema] {name}: OK ({len(data)} items)")

def main():
    check(DATA / "programs.json", SCHEMAS / "programs.schema.json", "programs")
    if (DATA / "universities.json").exists():
        check(DATA / "universities.json", SCHEMAS / "universities.schema.json", "universities")

if __name__ == "__main__":
    main()
