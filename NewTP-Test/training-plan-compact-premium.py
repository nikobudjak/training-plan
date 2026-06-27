from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

EXERCISEDB_BASE_URL = "https://oss.exercisedb.dev/api/v1"
DEFAULT_LIBRARY_PATH = "exercise_library.json"


# -----------------------------------------------------------------------------
# Loading / saving
# -----------------------------------------------------------------------------

def next_monday_from_today() -> date:
    today = date.today()
    return today + timedelta(days=(7 - today.weekday()) % 7 or 7)


def load_data(path: str | Path) -> Any:
    """Load JSON or YAML data."""
    path = Path(path)
    suffix = path.suffix.lower()

    text = path.read_text(encoding="utf-8")

    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError(
                "YAML input requires PyYAML. Run with: "
                "uv run --with pyyaml training_plan_embedded_single_yaml.py "
                "--input training_plan.yaml"
            )
        return yaml.safe_load(text)

    # For pasted files that may have .txt extension but contain YAML, try JSON first,
    # then fall back to YAML.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if yaml is None:
            raise
        return yaml.safe_load(text)


def save_json(path: str | Path, data: Any) -> None:
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def split_single_yaml(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return metadata and training from one YAML file.

    New format:
      metadata:
        client: ...
      months:
        - month: 1
          weeks: ...

    The HTML still receives two embedded objects because this keeps the UI simple:
    metadata_json and training_json.
    """
    if not isinstance(data, dict):
        raise RuntimeError("The input file must contain a dictionary/object at the top level.")

    metadata = data.get("metadata", {}) or {}
    training = {k: v for k, v in data.items() if k != "metadata"}

    if "months" not in training:
        raise RuntimeError("The input YAML/JSON must contain a top-level 'months:' key.")

    return metadata, training


# -----------------------------------------------------------------------------
# ExerciseDB helpers
# -----------------------------------------------------------------------------

def http_get_json(url: str, timeout: int = 30) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "training-plan-generator/3.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(name).lower()).strip()


def simplified_name(name: str) -> str:
    removable = [
        "barbell", "dumbbell", "cable", "machine", "lever", "weighted", "assisted",
        "bodyweight", "smith", "band", "resistance band", "sled", "standing", "seated",
    ]
    text = normalize_name(name)
    for word in removable:
        text = re.sub(r"\b" + re.escape(word) + r"\b", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_exercise_list(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        for key in ["data", "exercises", "results", "items"]:
            value = response.get(key)
            if isinstance(value, list):
                return value
    raise RuntimeError("Unexpected ExerciseDB response format.")


def fetch_exercisedb_cache(
    cache_path: Path,
    force: bool = False,
    page_size: int = 100,
    max_pages: int = 100,
) -> list[dict[str, Any]]:
    if cache_path.exists() and not force:
        data = load_data(cache_path)
        if isinstance(data, list):
            print(f"Loaded {len(data)} exercises from cache: {cache_path}")
            return data

    print("Fetching ExerciseDB exercise list...")
    all_items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for page in range(max_pages):
        offset = page * page_size
        params = urllib.parse.urlencode({"limit": page_size, "offset": offset})
        url = f"{EXERCISEDB_BASE_URL}/exercises?{params}"
        response = http_get_json(url)
        batch = extract_exercise_list(response)
        if not batch:
            break

        new_count = 0
        for item in batch:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("exerciseId") or item.get("id") or item.get("name") or "")
            if item_id and item_id in seen_ids:
                continue
            if item_id:
                seen_ids.add(item_id)
            all_items.append(item)
            new_count += 1

        print(f"Downloaded page {page + 1}: {len(batch)} items, total unique: {len(all_items)}")
        if len(batch) < page_size or new_count == 0:
            break

    if not all_items:
        raise RuntimeError("ExerciseDB returned no exercises.")

    save_json(cache_path, all_items)
    print(f"Saved {len(all_items)} ExerciseDB exercises to {cache_path}")
    return all_items


def infer_muscle_group(ex: dict[str, Any], fallback: str = "Other") -> str:
    parts = ex.get("bodyParts") or ex.get("bodyPart") or []
    targets = ex.get("targetMuscles") or ex.get("target") or []
    if isinstance(parts, str):
        parts = [parts]
    if isinstance(targets, str):
        targets = [targets]
    text = " ".join(parts + targets).lower()
    if any(x in text for x in ["chest", "pectorals"]):
        return "Chest"
    if any(x in text for x in ["back", "lats", "latissimus", "traps", "rhomboids"]):
        return "Back"
    if any(x in text for x in ["upper legs", "lower legs", "quads", "hamstrings", "glutes", "calves", "adductors", "abductors"]):
        return "Legs"
    if any(x in text for x in ["shoulders", "delts", "deltoids"]):
        return "Shoulders"
    if any(x in text for x in ["biceps", "triceps", "forearms", "arms"]):
        return "Arms"
    if any(x in text for x in ["waist", "abs", "core", "abdominals"]):
        return "Core"
    if "cardio" in text:
        return "Endurance"
    return fallback


def db_item_to_library_item(item: dict[str, Any]) -> dict[str, Any]:
    exercise_id = str(item.get("exerciseId") or item.get("id") or normalize_name(item.get("name", "")).replace(" ", "_"))
    name = str(item.get("name", ""))
    instructions = item.get("instructions") or []
    if isinstance(instructions, str):
        instructions = [instructions]
    return {
        "id": exercise_id,
        "name": name,
        "aliases": sorted(set([normalize_name(name), simplified_name(name)])),
        "muscle_group": infer_muscle_group(item),
        "body_parts": item.get("bodyParts") or ([item.get("bodyPart")] if item.get("bodyPart") else []),
        "target_muscles": item.get("targetMuscles") or ([item.get("target")] if item.get("target") else []),
        "secondary_muscles": item.get("secondaryMuscles") or [],
        "equipment": item.get("equipments") or ([item.get("equipment")] if item.get("equipment") else []),
        "gif_url": item.get("gifUrl") or "",
        "instructions": instructions,
        "source": "ExerciseDB",
    }


def build_library_from_db(db: list[dict[str, Any]], library_path: Path) -> dict[str, Any]:
    exercises = [db_item_to_library_item(item) for item in db if item.get("name")]
    exercises.sort(key=lambda x: x["name"])
    library = {"source": "ExerciseDB", "count": len(exercises), "exercises": exercises}
    save_json(library_path, library)
    print(f"Created exercise library with {len(exercises)} exercises: {library_path}")
    return library


def library_list(library: dict[str, Any]) -> list[dict[str, Any]]:
    return library.get("exercises", []) if isinstance(library, dict) else []


def find_in_library(query: str, library: dict[str, Any]) -> dict[str, Any] | None:
    q = normalize_name(query)
    if not q:
        return None
    for item in library_list(library):
        official_id = normalize_name(str(item.get("id", "")))
        official_name = normalize_name(str(item.get("name", "")))
        aliases = [normalize_name(str(a)) for a in item.get("aliases", [])]
        if q == official_id or q == official_name or q in aliases:
            return item
    return None


def suggest_exercises(query: str, items: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    q = normalize_name(query)
    if not q:
        return []
    q_tokens = q.split()
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in items:
        name = normalize_name(str(item.get("name", "")))
        item_id = normalize_name(str(item.get("exerciseId") or item.get("id") or ""))
        score = 0
        if q == item_id or q == name:
            score = 100
        elif q in name:
            score = 85
        elif q_tokens and all(t in name for t in q_tokens):
            score = 70
        elif q_tokens and any(t in name for t in q_tokens):
            score = 35
        if score:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in scored[:limit]]


def apply_library_item(plan_item: dict[str, Any], lib_item: dict[str, Any]) -> None:
    plan_item["exercise_library"] = {
        "id": lib_item.get("id"),
        "name": lib_item.get("name"),
        "gifUrl": lib_item.get("gif_url"),
        "bodyParts": lib_item.get("body_parts", []),
        "targetMuscles": lib_item.get("target_muscles", []),
        "secondaryMuscles": lib_item.get("secondary_muscles", []),
        "equipments": lib_item.get("equipment", []),
        "instructions": lib_item.get("instructions", []),
        "source": lib_item.get("source", "ExerciseDB"),
    }
    plan_item.setdefault("muscle_group", lib_item.get("muscle_group", "Other"))
    if not plan_item.get("description"):
        instructions = lib_item.get("instructions", [])
        if instructions:
            plan_item["description"] = "\n".join(instructions[:4])
    if not plan_item.get("video_url") and not plan_item.get("link") and lib_item.get("gif_url"):
        plan_item["video_url"] = lib_item.get("gif_url")


def enrich_training_data(training: dict[str, Any], library: dict[str, Any] | None = None, db: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    missing: list[tuple[str, list[str]]] = []
    for month in training.get("months", []):
        for week in month.get("weeks", []):
            for day in week.get("days", []):
                for section_name in ["warmup", "main_training", "finisher"]:
                    for item in day.get(section_name, []) or []:
                        if item.get("exercise_library") or item.get("exercise_db"):
                            continue
                        query = item.get("exercise_id") or item.get("exercisedb_name") or item.get("exercise") or item.get("name")
                        if not query:
                            continue
                        query_str = str(query)
                        if library:
                            lib_match = find_in_library(query_str, library)
                            if lib_match:
                                apply_library_item(item, lib_match)
                                continue
                            suggestions = [x.get("name", "") for x in suggest_exercises(query_str, library_list(library), limit=6)]
                            if suggestions:
                                item["exercise_db_suggestions"] = suggestions
                                missing.append((query_str, suggestions))
                        if db:
                            db_match = next((x for x in db if normalize_name(str(x.get("name", ""))) == normalize_name(query_str)), None)
                            if db_match:
                                apply_library_item(item, db_item_to_library_item(db_match))
                                continue
                            suggestions = [x.get("name", "") for x in suggest_exercises(query_str, db, limit=6)]
                            if suggestions and not item.get("exercise_db_suggestions"):
                                item["exercise_db_suggestions"] = suggestions
                                missing.append((query_str, suggestions))
    if missing:
        print("\nSome exercises were not matched exactly. Suggested ExerciseDB names:")
        for query, suggestions in missing:
            print(f"\n- {query}")
            for suggestion in suggestions:
                print(f"  • {suggestion}")
    return training


# -----------------------------------------------------------------------------
# Normalization for old and new schemas
# -----------------------------------------------------------------------------

def normalize_exercise_item(item: dict[str, Any]) -> dict[str, Any]:
    """Support both old flat fields and new set_plan fields.

    Old:
      sets: 3
      repetitions: 12
      planned_weight: 65% 1RM

    New:
      set_plan:
        - set: 1
          reps: 12-15
          weight: 65% 1RM
    """
    if not isinstance(item, dict):
        return {}

    out = dict(item)
    set_plan = out.get("set_plan") or []

    if isinstance(set_plan, list) and set_plan:
        out["sets"] = len(set_plan)
        first = set_plan[0] if isinstance(set_plan[0], dict) else {}
        out.setdefault("repetitions", first.get("reps", ""))
        out.setdefault("planned_weight", first.get("weight", ""))
    else:
        sets = out.get("sets") or 1
        repetitions = out.get("repetitions") or out.get("reps") or ""
        planned_weight = out.get("planned_weight") or out.get("weight") or ""
        try:
            set_count = int(sets)
        except (TypeError, ValueError):
            set_count = 1
        out["set_plan"] = [
            {"set": i, "reps": repetitions, "weight": planned_weight}
            for i in range(1, max(1, set_count) + 1)
        ]
        out["sets"] = max(1, set_count)
        out["repetitions"] = repetitions
        out["planned_weight"] = planned_weight

    out["video_url"] = out.get("video_url") or out.get("link") or ""
    out.setdefault("description", "")
    out.setdefault("muscle_group", "")
    out.setdefault("tempo", "")
    return out


def normalize_training_schema(training: dict[str, Any]) -> dict[str, Any]:
    training = dict(training)
    for month in training.get("months", []) or []:
        for week in month.get("weeks", []) or []:
            week.setdefault("phase", "")
            week.setdefault("goal", week.get("weekly_goal", ""))
            week.setdefault("intensity", "")
            for day in week.get("days", []) or []:
                day.setdefault("phase", week.get("phase", ""))
                day.setdefault("weekly_goal", week.get("goal", ""))
                day.setdefault("intensity", week.get("intensity", ""))
                for section in ["warmup", "main_training", "finisher"]:
                    day[section] = [normalize_exercise_item(x) for x in (day.get(section, []) or [])]
                day.setdefault("cooldown", "")
    return training


# -----------------------------------------------------------------------------
# Example file
# -----------------------------------------------------------------------------

def make_default_file(input_path: Path) -> None:
    if input_path.exists():
        return
    start = next_monday_from_today()
    example = {
        "metadata": {
            "coach": "Nik Budjak",
            "client": {
                "age": 19,
                "sex": "male",
                "height_cm": 189,
                "weight_kg": 85,
                "training_experience": "Previous experience with machines and dumbbells",
                "health_status": "Healthy",
                "goal": "Hypertrophy with focus on pectoralis major, biceps brachii and triceps brachii",
            },
            "plan_duration": "12 weeks",
            "weekly_structure": [
                "Monday - Lower Body",
                "Tuesday - Upper Body",
                "Wednesday - Zone 2 Endurance",
                "Thursday - Upper Body",
                "Friday - Lower Body",
                "Saturday - Optional HIIT or Active Recovery",
                "Sunday - Rest",
            ],
        },
        "settings": {"show_gifs": False},
        "months": [
            {
                "month": 1,
                "weeks": [
                    {
                        "week": 1,
                        "phase": "Re-entry Hypertrophy",
                        "goal": "Technique, controlled movement, preparation of muscles, tendons and joints.",
                        "intensity": "65% 1RM",
                        "start_date": start.isoformat(),
                        "days": [
                            {
                                "date": start.isoformat(),
                                "name": "Monday",
                                "type": "Weights",
                                "focus": "Upper Body A - Chest and Triceps Emphasis",
                                "warmup": [
                                    {
                                        "exercise": "Rowing Machine",
                                        "muscle_group": "General Preparation",
                                        "description": "Prepare the body for training by increasing blood flow.",
                                        "video_url": "",
                                        "set_plan": [{"set": 1, "reps": "5-10 min", "weight": "Bodyweight"}],
                                    }
                                ],
                                "main_training": [
                                    {
                                        "exercise": "Barbell Bench Press",
                                        "muscle_group": "Pectoralis Major + Triceps Brachii",
                                        "description": "Retract the shoulder blades, lower the bar under control, then press upward.",
                                        "video_url": "https://www.youtube.com/watch?v=rT7DgCr-3pg",
                                        "set_plan": [
                                            {"set": 1, "reps": "12-15", "weight": "65% 1RM"},
                                            {"set": 2, "reps": "12-15", "weight": "65% 1RM"},
                                        ],
                                    }
                                ],
                                "finisher": [],
                                "cooldown": "Light stretching and breathing for 5-10 minutes.",
                            }
                        ],
                    }
                ],
            }
        ],
    }
    if yaml is not None and input_path.suffix.lower() in {".yaml", ".yml"}:
        input_path.write_text(yaml.safe_dump(example, sort_keys=False, allow_unicode=True), encoding="utf-8")
    else:
        save_json(input_path, example)


# -----------------------------------------------------------------------------
# HTML generation
# -----------------------------------------------------------------------------

def generate_html(metadata: dict[str, Any], training: dict[str, Any]) -> str:
    metadata_json = json.dumps(metadata, ensure_ascii=False, default=str)
    training_json = json.dumps(training, ensure_ascii=False, default=str)

    html = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Training Plan</title>
<style>
:root{--bg:#050505;--card:#101827;--card2:#0b1120;--cyan:#00f5ff;--pink:#ff2bd6;--green:#39ff14;--yellow:#facc15;--orange:#ff8c00;--text:#f8fafc;--muted:#94a3b8;--line:#334155}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top,#172554,#050505 60%);color:var(--text);font-family:Arial,sans-serif}.topbar{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;padding:16px 18px;border-bottom:1px solid var(--cyan);position:sticky;top:0;background:rgba(5,5,5,.92);backdrop-filter:blur(8px);z-index:5}.identity h1{margin:0;color:var(--cyan);text-shadow:0 0 14px var(--cyan);font-size:24px}.identity p{margin:4px 0;color:var(--muted)}.top-actions,.bottom-actions{display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-end}.bottom-actions{position:fixed;right:18px;bottom:18px;z-index:8}.layout{display:grid;grid-template-columns:350px 1fr;gap:18px;padding:18px 18px 90px}.card{background:linear-gradient(145deg,var(--card),var(--card2));border:1px solid rgba(0,245,255,.35);border-radius:16px;padding:18px;box-shadow:0 0 24px rgba(0,245,255,.08)}button,select,input,textarea{background:#0f172a;color:var(--text);border:1px solid var(--cyan);border-radius:8px;padding:9px}button{cursor:pointer;box-shadow:0 0 8px rgba(0,245,255,.25)}button:hover{border-color:var(--pink);box-shadow:0 0 12px var(--pink)}select{width:100%;margin:8px 0 14px}.day-button{display:block;width:100%;text-align:left;margin-bottom:8px}.active{border-color:var(--green);color:var(--green)}.small{color:var(--muted);font-size:12px;line-height:1.45}.badge{display:inline-block;border:1px solid var(--green);color:var(--green);border-radius:999px;padding:4px 8px;margin-right:8px}.week-badge{display:inline-block;border:1px solid var(--cyan);color:var(--cyan);border-radius:999px;padding:4px 8px;margin:3px 6px 3px 0}.section-title{display:inline-block;padding:10px 14px;border-radius:12px;margin-top:22px}.section-title.warmup{color:var(--yellow);border:1px solid var(--cyan)}.section-title.main{color:var(--orange);border:1px solid var(--cyan)}.section-title.finisher{color:var(--pink);border:1px solid var(--pink)}.section-title.cooldown{color:var(--green);border:1px solid var(--green)}.compact-exercise-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(265px,1fr));gap:14px;margin-top:14px}.compact-exercise-card{border:1px solid var(--cyan);border-radius:14px;background:#050817;padding:12px;box-shadow:0 0 12px rgba(0,245,255,.12)}.compact-exercise-card h4{margin:0 0 8px;color:var(--cyan)}.exercise-desc{white-space:pre-wrap;color:#dbeafe;font-size:13px;line-height:1.45}.set-detail{border-top:1px solid var(--line);margin-top:10px;padding-top:10px}.detail-row{display:grid;grid-template-columns:110px 1fr;gap:8px;align-items:center;margin:6px 0}.detail-row span{color:var(--muted)}.detail-row input{width:100%}.compact-notes,.cooldown-box{width:100%;margin-top:8px}.cooldown-box{min-height:90px}.exercise-card-link{display:inline-block;margin-top:8px;color:var(--green);text-decoration:none}.coach-toggle{font-size:12px;padding:6px 8px;margin-top:8px}.coach-explanation{display:none;color:#dbeafe;font-size:13px;line-height:1.45;border-left:2px solid var(--green);padding-left:10px;margin-top:8px}.coach-explanation.open{display:block}.modal{position:fixed;inset:0;background:rgba(0,0,0,.78);display:flex;align-items:center;justify-content:center;z-index:20;padding:18px}.modal.hidden{display:none}.modal-card{max-width:900px;width:100%;max-height:88vh;overflow:auto}.modal-header{display:flex;justify-content:space-between;gap:12px;align-items:center}.week-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}.week-card{border:1px solid var(--cyan);border-radius:14px;padding:12px;background:#050817}.week-card h3{margin:0 0 8px;color:var(--cyan)}.week-card.active-week{border-color:var(--green);box-shadow:0 0 12px rgba(57,255,20,.25)}pre{white-space:pre-wrap;background:#020617;border:1px solid var(--line);padding:10px;border-radius:10px}.dashboard-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}.chart{height:190px;display:flex;align-items:end;gap:8px}.bar{background:linear-gradient(var(--cyan),var(--pink));border-radius:8px 8px 0 0;min-height:3px}.bar-label{font-size:11px;color:var(--muted);text-align:center;margin-top:5px}@media(max-width:850px){.layout{grid-template-columns:1fr}.topbar{flex-direction:column}.bottom-actions{left:18px;right:18px}.bottom-actions button{flex:1}}
.meso-table{width:100%;border-collapse:collapse;margin-top:30px;font-size:18px}
.meso-table th{background:#aaa;color:white;padding:10px;border:1px solid #ddd}
.meso-table td{padding:14px;text-align:center;border:1px solid #ddd;background:#f3f3f3;color:#222}
.meso-table td:first-child,.meso-table th:first-child{text-align:left;width:180px}
.week-number-btn{background:transparent;border:none;color:white;font-size:20px;font-weight:bold;box-shadow:none}
.week-number-btn:hover{color:var(--green);box-shadow:none}
.meso-notes{margin-top:30px}
</style>
</head>
<body>
<div class="topbar">
  <div class="identity">
    <h1>Training Plan</h1>
    <p id="subtitle"></p>
  </div>
  <div class="top-actions">
    <button type="button" onclick="openPlan()">Plan</button>
    <button type="button" onclick="openMetadata()">Client</button>
    <button type="button" onclick="openDashboard()">Dashboard</button>
    <button type="button" onclick="saveProgress()">Save</button>
    <button type="button" onclick="clearProgress()">Clear</button>
  </div>
</div>

<div class="layout">
  <aside class="card">
    <h2>Weeks</h2>
    <select id="weekSelect" onchange="selectWeek(Number(this.value))"></select>
    <div id="selectedWeekInfo" class="small"></div>
    <h2>Sessions</h2>
    <div id="dayList"></div>
  </aside>

  <main class="card">
    <h2 id="sessionTitle"></h2>
    <p id="sessionMeta" class="small"></p>
    <div id="sessionContent"></div>
  </main>
</div>

<div class="bottom-actions">
  <button type="button" onclick="previousSession()">Previous</button>
  <button type="button" onclick="nextSession()">Next</button>
</div>

<div id="planModal" class="modal hidden">
  <div class="card modal-card">
    <div class="modal-header">
      <h2>12 Week Plan</h2>
      <button type="button" onclick="closePlan()">Close</button>
    </div>
    <p class="small">Click a week to jump to it, or use the drop-down menu in the sidebar.</p>
    <div id="planContent" class="week-grid"></div>
  </div>
</div>

<div id="metadataModal" class="modal hidden">
  <div class="card modal-card">
    <div class="modal-header">
      <h2>Client Metadata</h2>
      <button type="button" onclick="closeMetadata()">Close</button>
    </div>
    <div id="metadataContent"></div>
  </div>
</div>

<div id="dashboardModal" class="modal hidden">
  <div class="card modal-card">
    <div class="modal-header">
      <h2>Dashboard</h2>
      <button type="button" onclick="closeDashboard()">Close</button>
    </div>
    <div id="dashboardContent"></div>
  </div>
</div>

<div id="exerciseExplanationModal" class="modal hidden">
  <div class="card modal-card">
    <div class="modal-header">
      <h2 id="exerciseExplanationTitle">Explanation</h2>
      <button type="button" onclick="closeExerciseExplanation()">Close</button>
    </div>
    <div id="exerciseExplanationContent"></div>
  </div>
</div>

<div id="exerciseExplanationModal" class="modal hidden">
  <div class="card modal-card">
    <div class="modal-header">
      <h2 id="exerciseExplanationTitle">Explanation</h2>
      <button type="button" onclick="closeExerciseExplanation()">Close</button>
    </div>

    <div id="exerciseExplanationContent"></div>
  </div>
</div>

<script>
const metadata = __METADATA_JSON__;
const trainingData = __TRAINING_JSON__;
let flatSessions = [];
let flatWeeks = [];
let selectedWeekIndex = 0;
let selectedIndex = 0;
let progress = JSON.parse(localStorage.getItem("trainingProgressV3") || "{}");

function escapeHtml(value){return String(value ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");}
function fmt(value){if(!value)return "";const d=new Date(value+"T00:00:00");return isNaN(d)?String(value):d.toLocaleDateString(undefined,{weekday:"long",year:"numeric",month:"short",day:"numeric"});}
function clientObject(){return metadata.client && typeof metadata.client === "object" ? metadata.client : metadata;}
function clientName(){const c=clientObject();return c.name || metadata.client_name || metadata.client || "Client";}
function weekTitle(w){const parts=["Week "+w.week];if(w.phase)parts.push(w.phase);if(w.intensity)parts.push("("+w.intensity+")");return parts.join(" - ").replace(" - ("," (");}
function exerciseKeyName(ex){return ex.exercise || ex.name || "Exercise";}
function exerciseExternalUrl(ex){return ex.video_url || ex.link || (ex.exercise_library && ex.exercise_library.gifUrl) || "";}
function key(sessionIndex,section,name,setNumber){return "s"+sessionIndex+":"+section+":"+name+":set"+setNumber;}

function buildFlatData(){
  flatSessions=[];flatWeeks=[];
  (trainingData.months || []).forEach(month=>{
    (month.weeks || []).forEach(week=>{
      const weekSessionStart=flatSessions.length;
      const weekIndex=flatWeeks.length;
      const w={...week, month:month.month, weekIndex, sessionStart:weekSessionStart, sessionIndexes:[]};
      flatWeeks.push(w);
      (week.days || []).forEach(day=>{
        const session={...day, month:month.month, week:week.week, weekIndex, phase:day.phase || week.phase || "", weekly_goal:day.weekly_goal || week.goal || "", intensity:day.intensity || week.intensity || ""};
        flatSessions.push(session);
        w.sessionIndexes.push(flatSessions.length-1);
      });
    });
  });
}

function todayIndex(){
  const today=new Date().toISOString().slice(0,10);
  const exact=flatSessions.findIndex(s=>s.date===today);
  if(exact>=0)return exact;
  return 0;
}

function renderSubtitle(){
  const c=clientObject();
  const bits=[];
  if(c.age)bits.push(c.age+" years");
  if(c.height_cm)bits.push(c.height_cm+" cm");
  if(c.weight_kg)bits.push(c.weight_kg+" kg");
  const goal=c.goal || metadata.goal || "";
  document.getElementById("subtitle").textContent = clientName()+" | "+bits.join(" | ")+(goal ? " | "+goal : "");
}

function renderWeekSelect(){
  const select=document.getElementById("weekSelect");
  select.innerHTML=flatWeeks.map((w,i)=>`<option value="${i}">${escapeHtml(weekTitle(w))}</option>`).join("");
  select.value=String(selectedWeekIndex);
  renderSelectedWeekInfo();
}

function renderSelectedWeekInfo(){
  const w=flatWeeks[selectedWeekIndex];
  if(!w){document.getElementById("selectedWeekInfo").innerHTML="";return;}
  document.getElementById("selectedWeekInfo").innerHTML =
    `<span class="week-badge">${escapeHtml(w.phase || "Phase")}</span>`+
    `<span class="week-badge">${escapeHtml(w.intensity || "Intensity")}</span>`+
    `<p>${escapeHtml(w.goal || "")}</p>`;
}

function selectWeek(weekIndex){
  selectedWeekIndex=weekIndex;
  const w=flatWeeks[selectedWeekIndex];
  if(w && w.sessionIndexes.length){selectedIndex=w.sessionIndexes[0];}
  render();
}

function renderDayList(){
  const list=document.getElementById("dayList");
  const w=flatWeeks[selectedWeekIndex];
  if(!w){list.innerHTML="<p class='small'>No weeks available.</p>";return;}
  list.innerHTML=w.sessionIndexes.map(i=>{
    const s=flatSessions[i];
    const active=i===selectedIndex?" active":"";
    return `<button type="button" class="day-button${active}" onclick="selectedIndex=${i};selectedWeekIndex=${s.weekIndex};render()"><strong>${escapeHtml(s.name || "Day")}</strong><br><span class="small">${escapeHtml(s.focus || "")}<br>${escapeHtml(fmt(s.date))}</span></button>`;
  }).join("");
}

function openPlan(){renderPlan();document.getElementById("planModal").classList.remove("hidden");}
function closePlan(){document.getElementById("planModal").classList.add("hidden");}
function renderPlan(){
  const box=document.getElementById("planContent");
  box.innerHTML=`
    <div class="meso-plan">
      <h2>Mesoplanung über 12 Wochen</h2>
      <p>Hypertrophietraining für 10 Trainingswochen, danach für 2 Trainingswochen IK-Training.</p>

      <table class="meso-table">
        <thead>
          <tr>
            <th>Woche</th>
            ${flatWeeks.map((w,i)=>`
              <th><button type="button" class="week-number-btn" onclick="openWeekDetails(${i})">${w.week}</button></th>
            `).join("")}
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Hypertrophie</td>
            ${flatWeeks.map(w=>`<td>${w.week <= 10 ? "x" : ""}</td>`).join("")}
          </tr>
          <tr>
            <td>IK-Training</td>
            ${flatWeeks.map(w=>`<td>${w.week >= 11 ? "x" : ""}</td>`).join("")}
          </tr>
        </tbody>
      </table>

      <div class="meso-notes">
        <p><strong>Hypertrophie:</strong> Start mit 70% 1-RM, Steigerung im Trainingsverlauf bis 80% 1-RM</p>
        <p><strong>IK-Training:</strong> Start mit 90% 1-RM, Steigerung im Trainingsverlauf bis 95% 1-RM</p>
      </div>
    </div>`;
}

function openWeekDetails(weekIndex){
  const w=flatWeeks[weekIndex];
  if(!w)return;

  document.getElementById("exerciseExplanationTitle").textContent=weekTitle(w);
  document.getElementById("exerciseExplanationContent").innerHTML=
    `<p><strong>Phase:</strong> ${escapeHtml(w.phase || "")}</p>`+
    `<p><strong>Intensity:</strong> ${escapeHtml(w.intensity || "")}</p>`+
    `<p><strong>Goal:</strong> ${escapeHtml(w.goal || "")}</p>`+
    `<p><strong>Start:</strong> ${escapeHtml(w.start_date || "")}</p>`+
    `<button type="button" onclick="selectWeek(${weekIndex});closeExerciseExplanation();closePlan()">Open this week</button>`;

  document.getElementById("exerciseExplanationModal").classList.remove("hidden");
}

function closeExerciseExplanation(){
  document.getElementById("exerciseExplanationModal").classList.add("hidden");
}

function coachExplanationText(ex){
  const lines=[];
  if(ex.description)lines.push(ex.description);
  if(ex.muscle_group)lines.push("Main focus: "+ex.muscle_group+".");
  if(ex.intensity)lines.push("Intensity: "+ex.intensity+".");
  if(ex.exercise_library && ex.exercise_library.instructions && ex.exercise_library.instructions.length){
    lines.push("Instructions: "+ex.exercise_library.instructions.slice(0,3).join(" "));
  }
  return lines.join("\n") || "No coach explanation available yet.";
}

function renderExerciseCard(ex,section,idx){
  const name=exerciseKeyName(ex);
  const link=exerciseExternalUrl(ex);
  const detailId=`set-detail-${section}-${selectedIndex}-${idx}`;
  const setPlan=Array.isArray(ex.set_plan)&&ex.set_plan.length ? ex.set_plan : [{set:1,reps:ex.repetitions||"",weight:ex.planned_weight||""}];

  let html=`<div class="compact-exercise-card ${section}"><h4>${escapeHtml(name)}</h4>`;
  html+=`<p class="small">${escapeHtml(ex.muscle_group || "")} ${ex.tempo ? "| Tempo: "+escapeHtml(ex.tempo) : ""}</p>`;

  html+=`<button type="button" class="coach-toggle" onclick="openExerciseExplanation(flatSessions[${selectedIndex}].${section}[${idx}])">Explanation</button>`;

  html+=`<div class="set-control"><select onchange="renderSelectedSetDetail('${detailId}', flatSessions[${selectedIndex}].${section}[${idx}], '${section}', ${selectedIndex}, Number(this.value))">`;
  setPlan.forEach((sp,si)=>{html+=`<option value="${si}">Set ${escapeHtml(sp.set || si+1)}</option>`;});
  html+=`</select>`;

  if(link)html+=`<a class="exercise-card-link" target="_blank" href="${escapeHtml(link)}">Video / link</a>`;

  html+=`</div><div id="${detailId}" class="set-detail"></div>`;
  html+=`</div>`;

  setTimeout(()=>renderSelectedSetDetail(detailId,ex,section,selectedIndex,0),0);
  return html;
}

function openExerciseExplanation(ex){
  document.getElementById("exerciseExplanationTitle").textContent = exerciseKeyName(ex);
  document.getElementById("exerciseExplanationContent").innerHTML =
    `<p><strong>Muscle group:</strong> ${escapeHtml(ex.muscle_group || "")}</p>`+
    `<div class="exercise-desc">${escapeHtml(coachExplanationText(ex)).replaceAll("\n","<br>")}</div>`;

  document.getElementById("exerciseExplanationModal").classList.remove("hidden");
}

function closeExerciseExplanation(){
  document.getElementById("exerciseExplanationModal").classList.add("hidden");
}

function toggleCoachExplanation(btn){const box=btn.nextElementSibling;if(box)box.classList.toggle("open");}

function previousValue(name,setLabel,currentSessionIndex){
  for(let i=currentSessionIndex-1;i>=0;i--){
    for(const section of ["main_training","warmup","finisher"]){
      const list=flatSessions[i][section]||[];
      for(const ex of list){
        if(exerciseKeyName(ex)===name){
          const value=progress[key(i,section,name,setLabel)];
          if(value)return value;
        }
      }
    }
  }
  return "-";
}

function tempoValue(sp, ex){
  const eccentric = sp.eccentric || ex.eccentric || "";
  const staticPart = sp.static || ex.static || "";
  const concentric = sp.concentric || ex.concentric || "";

  if(sp.tempo) return sp.tempo;
  if(ex.tempo) return ex.tempo;
  if(eccentric || staticPart || concentric){
    return `${eccentric || "-"}-${staticPart || "-"}-${concentric || "-"}`;
  }
  return "";
}

function renderSelectedSetDetail(detailId, ex, section, sessionIndex, setIndex){
  const box = document.getElementById(detailId);
  if(!box) return;

  const setPlan = Array.isArray(ex.set_plan) && ex.set_plan.length
    ? ex.set_plan
    : [{set:1, reps:ex.repetitions||"", weight:ex.planned_weight||""}];

  const sp = setPlan[setIndex] || setPlan[0] || {};
  const setLabel = sp.set || setIndex + 1;
  const name = exerciseKeyName(ex);
  const valueKey = key(sessionIndex, section, name, setLabel);
  const notesKey = valueKey + ":notes";
  const prev = previousValue(name, setLabel, sessionIndex);
  const tempo = tempoValue(sp, ex);

box.innerHTML =
  `<div class="detail-row"><span>Target reps</span><strong>${escapeHtml(sp.reps || ex.repetitions || "")}</strong></div>` +
  `<div class="detail-row"><span>Planned weight</span><strong>${escapeHtml(sp.weight || ex.planned_weight || "")}</strong></div>` +
  (tempo ? `<div class="detail-row"><span>Tempo</span><strong>E/S/K: ${escapeHtml(tempo)}</strong></div>` : "") +
  `<div class="detail-row"><span>Actual weight</span><input data-key="${escapeHtml(valueKey)}" value="${escapeHtml(progress[valueKey] || "")}" placeholder="kg / value"></div>` +
  `<div class="detail-row"><span>Previous</span><strong>${escapeHtml(prev || "-")}</strong></div>` +
  `<input class="compact-notes" data-key="${escapeHtml(notesKey)}" value="${escapeHtml(progress[notesKey] || "")}" placeholder="Notes">`;
}

function renderExerciseRows(list,section){
  if(!list || !list.length)return `<p class="small">No ${section.replace('_',' ')} specified.</p>`;
  return `<div class="compact-exercise-grid ${section}">`+list.map((ex,idx)=>renderExerciseCard(ex,section,idx)).join("")+`</div>`;
}

function renderSession(){
  if(!flatSessions.length){document.getElementById("sessionContent").innerHTML="<p>No training data available.</p>";return;}
  const s=flatSessions[selectedIndex];
  selectedWeekIndex=s.weekIndex;
  document.getElementById("sessionTitle").textContent=(s.name || "Day")+" - "+(s.focus || "");
  document.getElementById("sessionMeta").innerHTML=
    `<span class="badge">${escapeHtml(s.type || "")}</span>`+
    `${escapeHtml(fmt(s.date))} | Month ${escapeHtml(s.month)} | Week ${escapeHtml(s.week)} | ${escapeHtml(s.phase || "")} | ${escapeHtml(s.intensity || "")}`;
  let html="";
  if(s.weekly_goal)html+=`<p class="small"><strong>Weekly goal:</strong> ${escapeHtml(s.weekly_goal)}</p>`;
  html+=`<h3 class="section-title warmup">Warm-up</h3>${renderExerciseRows(s.warmup,"warmup")}`;
  html+=`<h3 class="section-title main">Main training</h3>${renderExerciseRows(s.main_training,"main_training")}`;
  if(s.finisher && s.finisher.length)html+=`<h3 class="section-title finisher">Finisher</h3>${renderExerciseRows(s.finisher,"finisher")}`;
  html+=`<h3 class="section-title cooldown">Cool-down</h3><textarea class="cooldown-box" data-key="cooldown-${selectedIndex}" placeholder="Client can write cooldown details here">${escapeHtml(progress["cooldown-"+selectedIndex] || s.cooldown || "")}</textarea>`;
  document.getElementById("sessionContent").innerHTML=html;
}

function previousSession(){if(selectedIndex>0){selectedIndex--;selectedWeekIndex=flatSessions[selectedIndex].weekIndex;render();}}
function nextSession(){if(selectedIndex<flatSessions.length-1){selectedIndex++;selectedWeekIndex=flatSessions[selectedIndex].weekIndex;render();}}

function saveProgress(){
  document.querySelectorAll("input[data-key], textarea[data-key]").forEach(el=>{progress[el.dataset.key]=el.value;});
  localStorage.setItem("trainingProgressV3",JSON.stringify(progress));
  alert("Progress saved on this device.");
}
function clearProgress(){if(confirm("Clear all locally saved progress?")){progress={};localStorage.removeItem("trainingProgressV3");render();}}

function openMetadata(){renderMetadata();document.getElementById("metadataModal").classList.remove("hidden");}
function closeMetadata(){document.getElementById("metadataModal").classList.add("hidden");}
function renderMetadata(){
  const c=clientObject();
  const weekly=metadata.weekly_structure || [];
  document.getElementById("metadataContent").innerHTML=
    `<p><strong>Client:</strong> ${escapeHtml(clientName())}</p>`+
    `<p><strong>Age:</strong> ${escapeHtml(c.age || "")}</p>`+
    `<p><strong>Sex:</strong> ${escapeHtml(c.sex || "")}</p>`+
    `<p><strong>Height:</strong> ${escapeHtml(c.height_cm || c.height || "")}</p>`+
    `<p><strong>Weight:</strong> ${escapeHtml(c.weight_kg || c.weight || "")}</p>`+
    `<p><strong>Experience:</strong> ${escapeHtml(c.training_experience || "")}</p>`+
    `<p><strong>Health:</strong> ${escapeHtml(c.health_status || "")}</p>`+
    `<p><strong>Goal:</strong> ${escapeHtml(c.goal || metadata.goal || "")}</p>`+
    `<p><strong>Plan duration:</strong> ${escapeHtml(metadata.plan_duration || "")}</p>`+
    `<h3>Weekly structure</h3><ul>${weekly.map(x=>`<li>${escapeHtml(x)}</li>`).join("")}</ul>`+
    `<h3>Raw metadata</h3><pre>${escapeHtml(JSON.stringify(metadata,null,2))}</pre>`;
}

function openDashboard(){renderDashboard();document.getElementById("dashboardModal").classList.remove("hidden");}
function closeDashboard(){document.getElementById("dashboardModal").classList.add("hidden");}
function renderMiniChart(title,data){
  const max=Math.max(1,...data.map(d=>d.value));
  return `<div class="card"><h3>${escapeHtml(title)}</h3><div class="chart">${data.map(d=>`<div style="flex:1"><div class="bar" title="${escapeHtml(d.label)}: ${d.value}" style="height:${d.value/max*150}px"></div><div class="bar-label">${escapeHtml(d.label)}</div></div>`).join("")}</div></div>`;
}
function renderDashboard(){
  const muscles={Chest:0,Legs:0,Back:0,Arms:0,Shoulders:0,Core:0,Other:0};
  flatSessions.forEach((sess,i)=>{
    ["main_training","warmup","finisher"].forEach(section=>{
      (sess[section]||[]).forEach(ex=>{
        const group=(ex.muscle_group||"Other").toLowerCase();
        const sets=Array.isArray(ex.set_plan)?ex.set_plan.length:Number(ex.sets||1);
        const bucket=group.includes("chest")||group.includes("pector")?"Chest":group.includes("leg")||group.includes("quad")||group.includes("glute")||group.includes("hamstring")||group.includes("calf")?"Legs":group.includes("back")||group.includes("lat")?"Back":group.includes("arm")||group.includes("biceps")||group.includes("triceps")?"Arms":group.includes("shoulder")||group.includes("delt")?"Shoulders":group.includes("core")||group.includes("ab")?"Core":"Other";
        muscles[bucket]+=sets;
      });
    });
  });
  const data=Object.keys(muscles).map(k=>({label:k,value:muscles[k]}));
  document.getElementById("dashboardContent").innerHTML=`<div class="dashboard-grid">${renderMiniChart("Planned sets by muscle group",data)}</div><p class="small">This dashboard counts planned sets from the embedded YAML. Actual client progress is saved locally in the browser.</p>`;
}

function render(){renderWeekSelect();renderDayList();renderSession();}
buildFlatData();renderSubtitle();selectedIndex=todayIndex();selectedWeekIndex=flatSessions[selectedIndex]?.weekIndex || 0;render();
</script>
</body>
</html>'''
    return html.replace("__METADATA_JSON__", metadata_json).replace("__TRAINING_JSON__", training_json)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a self-contained training plan HTML app from one YAML file.")
    parser.add_argument("--input", default="training_plan.yaml", help="Single YAML/JSON file containing metadata and months")
    parser.add_argument("--output", default="index.html", help="Output self-contained HTML file")
    parser.add_argument("--init", action="store_true", help="Create an example single YAML file if it does not exist")
    parser.add_argument("--use-exercisedb", action="store_true", help="Fetch/cache ExerciseDB and enrich exercises directly")
    parser.add_argument("--force-refresh-exercisedb", action="store_true", help="Refresh ExerciseDB cache even if it exists")
    parser.add_argument("--cache", default="exercisedb_cache.json", help="ExerciseDB cache JSON path")
    parser.add_argument("--page-size", type=int, default=100, help="ExerciseDB page size")
    parser.add_argument("--library", default=DEFAULT_LIBRARY_PATH, help="Local exercise library JSON path")
    parser.add_argument("--build-library", action="store_true", help="Build local exercise_library.json from ExerciseDB/cache")
    parser.add_argument("--use-library", action="store_true", help="Enrich plan from local exercise_library.json")
    parser.add_argument("--search", default="", help="Search exact ExerciseDB/library names and exit")
    args = parser.parse_args()

    input_path = Path(args.input)
    cache_path = Path(args.cache)
    library_path = Path(args.library)

    if args.init:
        make_default_file(input_path)

    if args.build_library:
        db = fetch_exercisedb_cache(cache_path, force=args.force_refresh_exercisedb, page_size=args.page_size)
        build_library_from_db(db, library_path)

    if args.search:
        if library_path.exists():
            library = load_data(library_path)
            matches = suggest_exercises(args.search, library_list(library), limit=25)
        else:
            db = fetch_exercisedb_cache(cache_path, force=False, page_size=args.page_size)
            matches = suggest_exercises(args.search, db, limit=25)
        print(f"Matches for '{args.search}':")
        for item in matches:
            print("-", item.get("name"), "| id:", item.get("exerciseId") or item.get("id"), "| target:", item.get("target") or item.get("targetMuscles"), "| equipment:", item.get("equipment") or item.get("equipments"))
        return

    data = load_data(input_path)
    metadata, training = split_single_yaml(data)

    library = None
    if library_path.exists():
        library = load_data(library_path)
        print(f"Using local ExerciseDB library: {library_path} ({len(library_list(library))} exercises)")
    elif args.use_library:
        print(f"WARNING: --use-library was set, but {library_path} does not exist. Run --build-library first.")

    db = None
    if args.use_exercisedb:
        db = fetch_exercisedb_cache(cache_path, force=args.force_refresh_exercisedb, page_size=args.page_size)

    if library or db:
        training = enrich_training_data(training, library=library, db=db)
        enriched_path = input_path.with_name(input_path.stem + "_training_enriched.json")
        save_json(enriched_path, training)
        print(f"Saved enriched training data to {enriched_path}")

    training = normalize_training_schema(training)
    html = generate_html(metadata, training)
    Path(args.output).write_text(html, encoding="utf-8")
    print(f"Created {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
