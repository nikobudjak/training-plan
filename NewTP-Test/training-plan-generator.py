from datetime import date, timedelta
from pathlib import Path
import json
import yaml


# ============================================================
# Helpers
# ============================================================

def set_plan(sets, reps, weight, eccentric="", static="", concentric=""):
    return [
        {
            "set": i + 1,
            "reps": reps,
            "weight": weight,
            "eccentric": eccentric,
            "static": static,
            "concentric": concentric,
            "tempo": f"{eccentric}-{static}-{concentric}" if eccentric and static and concentric else "",
        }
        for i in range(sets)
    ]


def exercise(name, muscle_group, description, video_url, sets, reps, weight,
             eccentric="", static="", concentric=""):
    return {
        "exercise": name,
        "muscle_group": muscle_group,
        "description": description,
        "video_url": video_url,
        "set_plan": set_plan(sets, reps, weight, eccentric, static, concentric),
    }


def rest_day(current_date, day_name):
    return {
        "date": current_date.isoformat(),
        "name": day_name,
        "type": "Recovery",
        "focus": "Rest",
        "warmup": [],
        "main_training": [],
        "finisher": [],
        "cooldown": "",
    }


# ============================================================
# Exercise library
# ============================================================

DB_PATH = Path("free-exercise-db/dist/exercises.json")

if not DB_PATH.exists():
    raise FileNotFoundError(
        f"Could not find {DB_PATH}. Make sure you run this script from NewTP-Test "
        "and that free-exercise-db is cloned inside this folder."
    )

with open(DB_PATH, encoding="utf-8") as f:
    EXERCISES = {
        item["id"]: item
        for item in json.load(f)
    }


CUSTOM_EXERCISES = {
    "rowing_machine": {
        "id": "rowing_machine",
        "name": "Rowing Machine",
        "primaryMuscles": ["Full Body"],
        "secondaryMuscles": [],
        "equipment": "rowing machine",
        "instructions": [
            "Row for 5-10 minutes at an easy pace to increase body temperature."
        ],
        "video_url": "",
    },
    "hip_rotations": {
        "id": "hip_rotations",
        "name": "Hip Rotations",
        "primaryMuscles": ["Hips"],
        "secondaryMuscles": [],
        "equipment": "body only",
        "instructions": [
            "Perform controlled hip circles in both directions."
        ],
        "video_url": "",
    },
    "bodyweight_squat": {
        "id": "bodyweight_squat",
        "name": "Bodyweight Squat",
        "primaryMuscles": ["Quadriceps", "Glutes"],
        "secondaryMuscles": [],
        "equipment": "body only",
        "instructions": [
            "Perform slow bodyweight squats through a comfortable range of motion."
        ],
        "video_url": "",
    },
    "light_jogging": {
        "id": "light_jogging",
        "name": "Light Jogging",
        "primaryMuscles": ["Cardiovascular System"],
        "secondaryMuscles": ["Legs"],
        "equipment": "body only",
        "instructions": [
            "Jog at a very easy pace to increase body temperature and prepare for training."
        ],
        "video_url": "",
    },
    "dynamic_leg_swings": {
        "id": "dynamic_leg_swings",
        "name": "Dynamic Leg Swings",
        "primaryMuscles": ["Hips"],
        "secondaryMuscles": ["Hamstrings", "Quadriceps"],
        "equipment": "body only",
        "instructions": [
            "Swing each leg forward and backward under control to prepare the hips and legs."
        ],
        "video_url": "",
    },
    "bike": {
        "id": "bike",
        "name": "Bike",
        "primaryMuscles": ["Cardiovascular System"],
        "secondaryMuscles": ["Quadriceps", "Calves"],
        "equipment": "bike",
        "instructions": [
            "Cycle at an easy pace for 5-10 minutes to increase blood flow."
        ],
        "video_url": "",
    },
    "dynamic_mobility": {
        "id": "dynamic_mobility",
        "name": "Dynamic Mobility",
        "primaryMuscles": ["Full Body"],
        "secondaryMuscles": [],
        "equipment": "body only",
        "instructions": [
            "Perform controlled dynamic mobility movements for the whole body."
        ],
        "video_url": "",
    },
    "zone2_run": {
        "id": "zone2_run",
        "name": "Zone 2 Running",
        "primaryMuscles": ["Cardiovascular System"],
        "secondaryMuscles": ["Legs"],
        "equipment": "body only",
        "instructions": [
            "Run at a comfortable pace where conversation is still possible."
        ],
        "video_url": "",
    },
    "optional_hiit": {
        "id": "optional_hiit",
        "name": "Optional HIIT",
        "primaryMuscles": ["Full Body"],
        "secondaryMuscles": ["Cardiovascular System"],
        "equipment": "body only",
        "instructions": [
            "Perform short high-intensity intervals only if recovery is good."
        ],
        "video_url": "",
    },
    "band_pull_apart": {
        "id": "band_pull_apart",
        "name": "Band Pull Apart",
        "primaryMuscles": ["Shoulders"],
        "secondaryMuscles": ["Upper Back", "Rear Deltoids"],
        "equipment": "resistance band",
        "instructions": [
            "Hold a resistance band in front of your chest with both hands.",
            "Keep your arms almost straight.",
            "Pull the band apart until your hands move out to the sides.",
            "Squeeze your shoulder blades together.",
            "Return slowly to the starting position."
        ],
        "video_url": "",
    },

    "arm_circles": {
        "id": "arm_circles",
        "name": "Arm Circles",
        "primaryMuscles": ["Shoulders"],
        "secondaryMuscles": ["Upper Back"],
        "equipment": "bodyweight",
        "instructions": [
            "Stand tall with your arms extended to the sides.",
            "Move your arms in small controlled circles.",
            "Gradually increase the circle size.",
            "Repeat in the opposite direction."
        ],
        "video_url": "",
    },

    "barbell_bench_press": {
        "id": "barbell_bench_press",
        "name": "Barbell Bench Press",
        "primaryMuscles": ["Chest"],
        "secondaryMuscles": ["Triceps", "Front Deltoids"],
        "equipment": "barbell",
        "instructions": [
            "Lie on a flat bench with your feet firmly on the floor.",
            "Grip the bar slightly wider than shoulder width.",
            "Lower the bar under control to the middle of your chest.",
            "Press the bar upward until your arms are extended.",
            "Keep your shoulder blades retracted during the movement."
        ],
        "video_url": "",
    },

    "dumbbell_incline_bench_press": {
        "id": "dumbbell_incline_bench_press",
        "name": "Dumbbell Incline Bench Press",
        "primaryMuscles": ["Chest"],
        "secondaryMuscles": ["Triceps", "Front Deltoids"],
        "equipment": "dumbbell",
        "instructions": [
            "Set the bench to a moderate incline.",
            "Hold one dumbbell in each hand at chest level.",
            "Press the dumbbells upward until your arms are extended.",
            "Lower them slowly back to chest level.",
            "Keep the movement controlled and avoid arching excessively."
        ],
        "video_url": "",
    },

    "cable_seated_row": {
        "id": "cable_seated_row",
        "name": "Cable Seated Row",
        "primaryMuscles": ["Back"],
        "secondaryMuscles": ["Biceps", "Rear Deltoids"],
        "equipment": "cable machine",
        "instructions": [
            "Sit at the cable row machine with your feet placed securely.",
            "Hold the handle with both hands.",
            "Pull the handle toward your lower ribs.",
            "Squeeze your shoulder blades together.",
            "Return slowly until your arms are extended."
        ],
        "video_url": "",
    },

    "cable_pushdown": {
        "id": "cable_pushdown",
        "name": "Cable Pushdown",
        "primaryMuscles": ["Triceps"],
        "secondaryMuscles": [],
        "equipment": "cable machine",
        "instructions": [
            "Stand in front of a high cable pulley.",
            "Hold the bar or rope with your elbows close to your body.",
            "Push the handle downward until your elbows are extended.",
            "Pause briefly and squeeze the triceps.",
            "Return slowly without letting the elbows move forward."
        ],
        "video_url": "",
    },

    "barbell_curl": {
        "id": "barbell_curl",
        "name": "Barbell Curl",
        "primaryMuscles": ["Biceps"],
        "secondaryMuscles": ["Forearms"],
        "equipment": "barbell",
        "instructions": [
            "Stand tall holding a barbell with an underhand grip.",
            "Keep your elbows close to your sides.",
            "Curl the bar upward toward your chest.",
            "Squeeze the biceps at the top.",
            "Lower the bar slowly back to the starting position."
        ],
        "video_url": "",
    },

    "front_plank": {
        "id": "front_plank",
        "name": "Front Plank",
        "primaryMuscles": ["Core"],
        "secondaryMuscles": ["Shoulders", "Glutes"],
        "equipment": "bodyweight",
        "instructions": [
            "Place your forearms on the floor with elbows under your shoulders.",
            "Extend your legs behind you.",
            "Keep your body in a straight line from head to heels.",
            "Brace your core and avoid letting your hips drop.",
            "Hold the position for the prescribed time."
        ],
        "video_url": "",
    },
    "Walking": {
        "id": "Walking",
        "name": "Walking",
        "primaryMuscles": ["Full Body"],
        "secondaryMuscles": [],
        "equipment": "bodyweight",
        "instructions": [
            "Walk at an easy pace.",
            "Gradually increase your body temperature.",
            "Breathe naturally and prepare for the workout."
        ],
        "video_url": "",
    },

    "Dynamic Leg Swings": {
        "id": "Dynamic Leg Swings",
        "name": "Dynamic Leg Swings",
        "primaryMuscles": ["Hip Flexors", "Hamstrings"],
        "secondaryMuscles": ["Glutes"],
        "equipment": "bodyweight",
        "instructions": [
            "Stand next to a wall for balance.",
            "Swing one leg forward and backward in a controlled motion.",
            "Keep your torso upright.",
            "Repeat on the opposite leg."
        ],
        "video_url": "",
    },

    "High Knees": {
        "id": "High Knees",
        "name": "High Knees",
        "primaryMuscles": ["Quadriceps"],
        "secondaryMuscles": ["Hip Flexors", "Calves", "Core"],
        "equipment": "bodyweight",
        "instructions": [
            "Run in place.",
            "Drive your knees toward hip height.",
            "Pump your arms naturally.",
            "Land softly on the balls of your feet."
        ],
        "video_url": "",
    },

    "Standing Quadriceps Stretch": {
        "id": "Standing Quadriceps Stretch",
        "name": "Standing Quadriceps Stretch",
        "primaryMuscles": ["Quadriceps"],
        "secondaryMuscles": [],
        "equipment": "bodyweight",
        "instructions": [
            "Stand on one leg.",
            "Pull your opposite foot toward your glutes.",
            "Keep your knees together.",
            "Hold the stretch without bouncing."
        ],
        "video_url": "",
    },

    "Standing Hamstring Stretch": {
        "id": "Standing Hamstring Stretch",
        "name": "Standing Hamstring Stretch",
        "primaryMuscles": ["Hamstrings"],
        "secondaryMuscles": ["Calves"],
        "equipment": "bodyweight",
        "instructions": [
            "Place one heel in front of you.",
            "Keep the knee slightly bent.",
            "Lean forward from the hips until a gentle stretch is felt.",
            "Keep your back straight."
        ],
        "video_url": "",
    },

    "Standing Calf Stretch": {
        "id": "Standing Calf Stretch",
        "name": "Standing Calf Stretch",
        "primaryMuscles": ["Calves"],
        "secondaryMuscles": [],
        "equipment": "bodyweight",
        "instructions": [
            "Place your hands against a wall.",
            "Step one foot behind you.",
            "Keep the back heel on the floor.",
            "Lean forward until you feel a stretch in the calf."
        ],
        "video_url": "",
    },

    "Running": {
        "id": "Running",
        "name": "Running",
        "primaryMuscles": ["Full Body"],
        "secondaryMuscles": ["Quadriceps", "Hamstrings", "Calves", "Glutes", "Core"],
        "equipment": "bodyweight",
        "instructions": [
            "Maintain a steady conversational pace (Zone 2).",
            "Keep your posture upright.",
            "Land softly with a natural stride.",
            "Breathe rhythmically throughout the session."
        ],
        "video_url": "",
    },
    "Crunch": {
        "id": "Crunch",
        "name": "Crunch",
        "primaryMuscles": ["Abdominals"],
        "secondaryMuscles": ["Hip Flexors"],
        "equipment": "bodyweight",
        "instructions": [
            "Lie on your back with your knees bent and feet flat on the floor.",
            "Place your hands lightly behind your head or across your chest.",
            "Contract your abdominal muscles to lift your shoulders off the floor.",
            "Pause briefly at the top.",
            "Lower yourself slowly to the starting position."
        ],
        "video_url": "",
    },

    "Russian Twist": {
        "id": "Russian Twist",
        "name": "Russian Twist",
        "primaryMuscles": ["Obliques"],
        "secondaryMuscles": ["Abdominals"],
        "equipment": "bodyweight",
        "instructions": [
            "Sit on the floor with your knees bent and feet on the ground.",
            "Lean your torso back slightly while keeping your back straight.",
            "Clasp your hands together in front of your chest.",
            "Rotate your torso to one side, then to the other.",
            "Keep the movement slow and controlled."
        ],
        "video_url": "",
    },

    "Bicycle Crunch": {
        "id": "Bicycle Crunch",
        "name": "Bicycle Crunch",
        "primaryMuscles": ["Abdominals"],
        "secondaryMuscles": ["Obliques", "Hip Flexors"],
        "equipment": "bodyweight",
        "instructions": [
            "Lie on your back with your hands behind your head.",
            "Lift your shoulders and feet off the floor.",
            "Bring one knee toward your chest while rotating the opposite elbow toward it.",
            "Extend the other leg.",
            "Alternate sides in a smooth pedaling motion."
        ],
        "video_url": "",
    },

    "Front Plank": {
        "id": "Front Plank",
        "name": "Front Plank",
        "primaryMuscles": ["Abdominals"],
        "secondaryMuscles": ["Obliques", "Lower Back", "Shoulders", "Glutes"],
        "equipment": "bodyweight",
        "instructions": [
            "Place your forearms on the floor with your elbows directly under your shoulders.",
            "Extend your legs behind you.",
            "Keep your body in a straight line from head to heels.",
            "Brace your core and glutes.",
            "Hold the position while breathing normally."
        ],
        "video_url": "",
    },
    "Straight_Bar_Bench_Mid_Rows": {
        "id": "Straight_Bar_Bench_Mid_Rows",
        "name": "Straight Bar Bench Mid Rows",
        "primaryMuscles": ["Upper Back"],
        "secondaryMuscles": ["Latissimus Dorsi", "Biceps", "Rear Deltoids"],
        "equipment": "barbell",
        "instructions": [
            "Lie face down on an elevated bench.",
            "Hold the barbell with a shoulder-width overhand grip.",
            "Pull the bar toward the underside of the bench.",
            "Squeeze your shoulder blades together.",
            "Lower the bar under control."
        ],
        "video_url": "",
    },

    "Dumbbell Shoulder Press": {
        "id": "Dumbbell Shoulder Press",
        "name": "Dumbbell Shoulder Press",
        "primaryMuscles": ["Anterior Deltoids"],
        "secondaryMuscles": ["Lateral Deltoids", "Triceps"],
        "equipment": "dumbbell",
        "instructions": [
            "Sit or stand holding a dumbbell in each hand at shoulder height.",
            "Press the dumbbells overhead until your arms are extended.",
            "Do not lock your elbows.",
            "Lower the dumbbells slowly back to the starting position."
        ],
        "video_url": "",
    },

    "Dumbbell Lateral Raise": {
        "id": "Dumbbell Lateral Raise",
        "name": "Dumbbell Lateral Raise",
        "primaryMuscles": ["Lateral Deltoids"],
        "secondaryMuscles": ["Supraspinatus"],
        "equipment": "dumbbell",
        "instructions": [
            "Stand holding a dumbbell in each hand.",
            "Keep a slight bend in your elbows.",
            "Raise your arms to shoulder height.",
            "Pause briefly before lowering under control."
        ],
        "video_url": "",
    },

    "Cable Chest Fly": {
        "id": "Cable Chest Fly",
        "name": "Cable Chest Fly",
        "primaryMuscles": ["Pectoralis Major"],
        "secondaryMuscles": ["Anterior Deltoids"],
        "equipment": "cable machine",
        "instructions": [
            "Stand between two cable pulleys.",
            "Hold one handle in each hand.",
            "Bring your hands together in front of your chest.",
            "Squeeze your chest.",
            "Return slowly to the starting position."
        ],
        "video_url": "",
    },

    "Hammer Curl": {
        "id": "Hammer Curl",
        "name": "Hammer Curl",
        "primaryMuscles": ["Brachialis"],
        "secondaryMuscles": ["Biceps", "Brachioradialis"],
        "equipment": "dumbbell",
        "instructions": [
            "Stand holding a dumbbell in each hand with a neutral grip.",
            "Curl the dumbbells toward your shoulders.",
            "Keep your elbows close to your torso.",
            "Lower under control."
        ],
        "video_url": "",
    },

    "Overhead Cable Triceps Extension": {
        "id": "Overhead Cable Triceps Extension",
        "name": "Overhead Cable Triceps Extension",
        "primaryMuscles": ["Triceps"],
        "secondaryMuscles": [],
        "equipment": "cable machine",
        "instructions": [
            "Face away from a high cable pulley.",
            "Hold the rope behind your head.",
            "Extend your elbows until your arms are straight.",
            "Pause briefly.",
            "Return slowly."
        ],
        "video_url": "",
    },

    "Dead Hang": {
        "id": "Dead Hang",
        "name": "Dead Hang",
        "primaryMuscles": ["Forearms"],
        "secondaryMuscles": ["Grip", "Shoulders", "Latissimus Dorsi"],
        "equipment": "pull-up bar",
        "instructions": [
            "Grip a pull-up bar with both hands.",
            "Allow your body to hang with your arms fully extended.",
            "Relax your shoulders while maintaining control.",
            "Hold for the prescribed time."
        ],
        "video_url": "",
    },
}

EXERCISES.update(CUSTOM_EXERCISES)


ALIASES = {
    "leg_extensions": "leg_extensions",
    "leg_curl": "leg_curl",
    "calf_raise": "standing_calf_raises",
    "bench_press": "barbell_bench_press_medium_grip",
    "incline_press": "incline_dumbbell_press",
    "dips": "dips_chest_version",
    "fly": "dumbbell_flyes",
    "pushdown": "triceps_pushdown",
    "overhead_extension": "standing_dumbbell_triceps_extension",
    "lat_pulldown": "wide_grip_lat_pulldown",
    "row": "seated_cable_rows",
    "biceps_curl": "dumbbell_bicep_curl",
    "hammer_curl": "hammer_curls",
    "rdl": "romanian_deadlift",
    "leg_press": "leg_press",
    "lunges": "dumbbell_lunges",
}


def resolve_key(key):
    return ALIASES.get(key, key)


def make_exercise(key, sets, reps, weight, eccentric="", static="", concentric=""):
    key = resolve_key(key)

    if key not in EXERCISES:
        token = key.split("_")[-1]
        suggestions = [k for k in EXERCISES if token in k][:20]
        raise KeyError(
            f"Exercise key not found: {key}\n"
            f"Possible matches: {suggestions}"
        )

    e = EXERCISES[key]

    primary = e.get("primaryMuscles", [])
    secondary = e.get("secondaryMuscles", [])
    instructions = e.get("instructions", [])

    return exercise(
        name=e.get("name", key),
        muscle_group=" + ".join(primary + secondary),
        description=" ".join(instructions),
        video_url=e.get("video_url", ""),
        sets=sets,
        reps=reps,
        weight=weight,
        eccentric=eccentric,
        static=static,
        concentric=concentric,
    )


# ============================================================
# 12-week phases
# ============================================================

WEEKS = [
    {"week": 1, "phase": "Re-entry Hypertrophy", "goal": "Technique, controlled movement, preparation of muscles, tendons and joints.", "intensity": "65% 1RM", "sets": 2, "reps": "12-15"},
    {"week": 2, "phase": "Re-entry Hypertrophy", "goal": "Technique consolidation and gradual increase of training load.", "intensity": "70% 1RM", "sets": 3, "reps": "12-15"},
    {"week": 3, "phase": "Hypertrophy", "goal": "Muscle growth through moderate volume and progressive overload.", "intensity": "70% 1RM", "sets": 3, "reps": "10-12"},
    {"week": 4, "phase": "Hypertrophy", "goal": "Increase training volume while maintaining clean technique.", "intensity": "72.5% 1RM", "sets": 3, "reps": "10-12"},
    {"week": 5, "phase": "Hypertrophy", "goal": "Progressive overload for chest, biceps and triceps.", "intensity": "75% 1RM", "sets": 3, "reps": "8-12"},
    {"week": 6, "phase": "Hypertrophy", "goal": "Stable hypertrophy workload with focus on target muscles.", "intensity": "75% 1RM", "sets": 3, "reps": "8-12"},
    {"week": 7, "phase": "Hypertrophy", "goal": "Increase mechanical tension with slightly higher intensity.", "intensity": "77.5% 1RM", "sets": 4, "reps": "8-10"},
    {"week": 8, "phase": "Hypertrophy", "goal": "High-quality volume for chest, biceps and triceps.", "intensity": "80% 1RM", "sets": 4, "reps": "8-10"},
    {"week": 9, "phase": "Hypertrophy", "goal": "Peak hypertrophy stimulus with high mechanical tension.", "intensity": "80% 1RM", "sets": 4, "reps": "8-10"},
    {"week": 10, "phase": "Hypertrophy", "goal": "Final high-volume hypertrophy week before strength-emphasis block.", "intensity": "82.5% 1RM", "sets": 4, "reps": "6-10"},
    {"week": 11, "phase": "Intermuscular Coordination / Strength Emphasis", "goal": "Improve neural coordination and prepare the client for higher absolute loads in future hypertrophy training.", "intensity": "85% 1RM", "sets": 4, "reps": "4-6"},
    {"week": 12, "phase": "Intermuscular Coordination / Strength Emphasis", "goal": "Improve movement efficiency and maximal strength foundation.", "intensity": "87.5% 1RM", "sets": 4, "reps": "3-5"},
]


# ============================================================
# Weekly template
# ============================================================

DAY_TEMPLATE = {

    "Monday": {
        "type": "Weights",
        "focus": "Lower Body A - Squat, Glutes and Legs",
        "warmup": [
            {"key": "rowing_machine", "sets": 1, "reps": "5-10 min", "weight": "Bodyweight", "eccentric": "", "static": "", "concentric": ""},
            {"key": "hip_rotations", "sets": 2, "reps": "10 each side", "weight": "Bodyweight", "eccentric": "2", "static": "0", "concentric": "2"},
            {"key": "Bodyweight_Squat", "sets": 2, "reps": "15", "weight": "Bodyweight", "eccentric": "2", "static": "0", "concentric": "2"},
        ],
        "main": [
            {"key": "Barbell_Full_Squat", "sets": 5, "reps": "8-10", "weight": "70% 1RM", "eccentric": "3", "static": "1", "concentric": "1"},
            {"key": "Barbell_Glute_Bridge", "sets": 4, "reps": "8-10", "weight": "70% 1RM", "eccentric": "3", "static": "1", "concentric": "1"},
            {"key": "Leg_Extensions", "sets": 3, "reps": "12-15", "weight": "65% 1RM", "eccentric": "2", "static": "1", "concentric": "2"},
            {"key": "Seated_Leg_Curl", "sets": 3, "reps": "12-15", "weight": "65% 1RM", "eccentric": "2", "static": "1", "concentric": "2"},
            {"key": "Standing_Calf_Raises", "sets": 4, "reps": "12-15", "weight": "70% 1RM", "eccentric": "2", "static": "1", "concentric": "2"},
        ],
        "finisher": [
            {"key": "Barbell_Lunge", "sets": 2, "reps": "12 each leg", "weight": "Bodyweight or light load", "eccentric": "2", "static": "0", "concentric": "2"},
            {"key": "Plank", "sets": 2, "reps": "30-60 sec", "weight": "Bodyweight", "eccentric": "", "static": "30-60", "concentric": ""},
        ],
    },

    "Tuesday": {
        "type": "Weights",
        "focus": "Upper Body A - Chest and Triceps Emphasis",
        "warmup": [
            {"key": "Rowing_Stationary", "sets": 1, "reps": "~5 min", "weight": "", "eccentric": "", "static": "", "concentric": ""},
            {"key": "band_pull_apart", "sets": 2, "reps": "15", "weight": "Light Band", "eccentric": "2", "static": "0", "concentric": "2"},
            {"key": "arm_circles", "sets": 1, "reps": "10 each direction", "weight": "Bodyweight", "eccentric": "2", "static": "0", "concentric": "2"},
            {"key": "Clock_Push-Up", "sets": 1, "reps": "10", "weight": "Bodyweight", "eccentric": "2", "static": "0", "concentric": "2"},
        ],
        "main": [
            {"key": "barbell_bench_press", "sets": 4, "reps": "8-10", "weight": "70% 1RM", "eccentric": "3", "static": "1", "concentric": "1"},
            {"key": "Wide-Grip_Rear_Pull-Up", "sets": 3, "reps": "8-10", "weight": "Bodyweight", "eccentric": "3", "static": "1", "concentric": "1"},
            {"key": "dumbbell_incline_bench_press", "sets": 3, "reps": "10-12", "weight": "65% 1RM", "eccentric": "3", "static": "1", "concentric": "1"},
            {"key": "cable_seated_row", "sets": 3, "reps": "10-12", "weight": "70% 1RM", "eccentric": "3", "static": "1", "concentric": "1"},
            {"key": "cable_pushdown", "sets": 3, "reps": "12-15", "weight": "65% 1RM", "eccentric": "2", "static": "1", "concentric": "2"},
            {"key": "barbell_curl", "sets": 3, "reps": "12-15", "weight": "65% 1RM", "eccentric": "2", "static": "1", "concentric": "2"},
        ],
        "finisher": [
            {"key": "Dips_-_Chest_Version", "sets": 2, "reps": "AMRAP", "weight": "Bodyweight", "eccentric": "2", "static": "0", "concentric": "2"},
        ],
    },

    "Wednesday": {
        "type": "Endurance",
        "focus": "Zone 2 Aerobic Running",
        "warmup": [
            {"key": "Dynamic Leg Swings", "sets": 1, "reps": "10 each leg", "weight": "Bodyweight", "eccentric": "2", "static": "0", "concentric": "2"},
            {"key": "High Knees", "sets": 1, "reps": "30 sec", "weight": "Bodyweight", "eccentric": "", "static": "", "concentric": ""},
        ],
        "main": [
            {"key": "Running", "sets": 1, "reps": "35-45 min", "weight": "Zone 2 (65-75% HRmax)", "eccentric": "", "static": "", "concentric": ""},
        ],
        "finisher": [
            {"key": "Front Plank", "sets": 3, "reps": "45-60 sec", "weight": "Bodyweight", "eccentric": "", "static": "45-60", "concentric": ""},
            {"key": "Crunch", "sets": 3, "reps": "15-20", "weight": "Bodyweight", "eccentric": "2", "static": "1", "concentric": "2"},
            {"key": "Russian Twist", "sets": 3, "reps": "20 (10 each side)", "weight": "Bodyweight", "eccentric": "2", "static": "0", "concentric": "2"},
        ],
    },

    "Thursday": {
        "type": "Weights",
        "focus": "Upper Body B - Back and Shoulder Emphasis",
        "warmup": [
            {"key": "Rowing_Stationary", "sets": 1, "reps": "~5 min", "weight": "", "eccentric": "", "static": "", "concentric": ""},
            {"key": "band_pull_apart", "sets": 2, "reps": "15", "weight": "Light Band", "eccentric": "2", "static": "0", "concentric": "2"},
            {"key": "arm_circles", "sets": 1, "reps": "10 each direction", "weight": "Bodyweight", "eccentric": "2", "static": "0", "concentric": "2"},
        ],
        "main": [
            {"key": "Straight_Bar_Bench_Mid_Rows", "sets": 4, "reps": "8-10", "weight": "70% 1RM", "eccentric": "3", "static": "1", "concentric": "1"},
            {"key": "Wide-Grip_Rear_Pull-Up", "sets": 3, "reps": "8-10", "weight": "Bodyweight", "eccentric": "3", "static": "1", "concentric": "1"},
            {"key": "Dumbbell Shoulder Press", "sets": 3, "reps": "10-12", "weight": "65% 1RM", "eccentric": "3", "static": "1", "concentric": "1"},
            {"key": "Dumbbell Lateral Raise", "sets": 3, "reps": "12-15", "weight": "60% 1RM", "eccentric": "2", "static": "1", "concentric": "2"},
            {"key": "Cable Chest Fly", "sets": 3, "reps": "12-15", "weight": "65% 1RM", "eccentric": "2", "static": "1", "concentric": "2"},
            {"key": "Hammer Curl", "sets": 3, "reps": "12-15", "weight": "65% 1RM", "eccentric": "2", "static": "1", "concentric": "2"},
            {"key": "Overhead Cable Triceps Extension", "sets": 3, "reps": "12-15", "weight": "65% 1RM", "eccentric": "2", "static": "1", "concentric": "2"},
        ],
        "finisher": [
            {"key": "Dead Hang", "sets": 3, "reps": "30-60 sec", "weight": "Bodyweight", "eccentric": "", "static": "30-60", "concentric": ""},
        ],
    },

    "Friday": {
        "type": "Weights",
        "focus": "Lower Body B - Posterior Chain Emphasis",
        "warmup": [
            {"key": "Rowing_Stationary", "sets": 1, "reps": "~5 min", "weight": "", "eccentric": "", "static": "", "concentric": ""},
            {"key": "Dynamic Leg Swings", "sets": 1, "reps": "10 each leg", "weight": "Bodyweight", "eccentric": "2", "static": "0", "concentric": "2"},
            {"key": "Dumbbell_Squat", "sets": 2, "reps": "10", "weight": "30-50% 1RM", "eccentric": "2", "static": "0", "concentric": "2"},
        ],
        "main": [
            {"key": "Barbell_Deadlift", "sets": 4, "reps": "8-10", "weight": "70% 1RM", "eccentric": "3", "static": "1", "concentric": "1"},
            {"key": "Barbell_Glute_Bridge", "sets": 4, "reps": "8-10", "weight": "70% 1RM", "eccentric": "3", "static": "1", "concentric": "1"},
            {"key": "Reverse_Barbell_Preacher_Curls", "sets": 3, "reps": "12-15", "weight": "65% 1RM", "eccentric": "2", "static": "1", "concentric": "2"},
            {"key": "Leg_Extensions", "sets": 3, "reps": "12-15", "weight": "65% 1RM", "eccentric": "2", "static": "1", "concentric": "2"},
            {"key": "Front_Leg_Raises", "sets": 4, "reps": "12-15", "weight": "70% 1RM", "eccentric": "2", "static": "1", "concentric": "2"},
        ],
        "finisher": [
            {"key": "Front Plank", "sets": 3, "reps": "45-60 sec", "weight": "Bodyweight", "eccentric": "", "static": "45-60", "concentric": ""},
            {"key": "Crunch", "sets": 3, "reps": "15-20", "weight": "Bodyweight", "eccentric": "2", "static": "1", "concentric": "2"},
            {"key": "Russian Twist", "sets": 3, "reps": "20 (10 each side)", "weight": "Bodyweight", "eccentric": "2", "static": "0", "concentric": "2"},
        ],
    },

    "Saturday": {
        "type": "Optional",
        "focus": "Optional HIIT or Active Recovery",
        "warmup": [],
        "main": [],
        "finisher": [],
    },

    "Sunday": {
        "type": "Recovery",
        "focus": "Rest",
        "warmup": [],
        "main": [],
        "finisher": [],
    },
}

# ============================================================
# Day generation
# ============================================================

def build_section(items, week_info=None):
    return [
        make_exercise(
            key=item["key"],
            sets=item.get("sets", week_info["sets"] if week_info else 1),
            reps=item.get("reps", week_info["reps"] if week_info else ""),
            weight=item.get("weight", week_info["intensity"] if week_info else "Bodyweight"),
            eccentric=item.get("eccentric", "2"),
            static=item.get("static", "1"),
            concentric=item.get("concentric", "2"),
        )
        for item in items
    ]


def generate_day(current_date, day_name, week_info):
    template = DAY_TEMPLATE[day_name]

    if template["type"] == "Recovery":
        return rest_day(current_date, day_name)

    warmup = build_section(template["warmup"])
    main_training = build_section(template["main"], week_info)
    finisher = build_section(template["finisher"])

    return {
        "date": current_date.isoformat(),
        "name": day_name,
        "type": template["type"],
        "focus": template["focus"],
        "phase": week_info["phase"],
        "weekly_goal": week_info["goal"],
        "intensity": week_info["intensity"],
        "warmup": warmup,
        "main_training": main_training,
        "finisher": finisher,
        "cooldown": "Cool-down on a mat: light stretching and breathing for 5-10 minutes.",
    }


# ============================================================
# Week / plan generation
# ============================================================

def generate_week(week_info, start_date):
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    return {
        "week": week_info["week"],
        "phase": week_info["phase"],
        "goal": week_info["goal"],
        "intensity": week_info["intensity"],
        "start_date": start_date.isoformat(),
        "days": [
            generate_day(start_date + timedelta(days=i), day_name, week_info)
            for i, day_name in enumerate(day_names)
        ],
    }


def generate_plan(first_monday):
    generated_weeks = [
        generate_week(week_info, first_monday + timedelta(weeks=i))
        for i, week_info in enumerate(WEEKS)
    ]

    return {
        "metadata": {
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
        "months": [
            {"month": 1, "weeks": generated_weeks[0:4]},
            {"month": 2, "weeks": generated_weeks[4:8]},
            {"month": 3, "weeks": generated_weeks[8:12]},
        ],
    }


if __name__ == "__main__":
    first_monday = date(2026, 6, 22)
    plan = generate_plan(first_monday)

    output_file = "twelve_week_training_plan.yaml"

    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(plan, f, sort_keys=False, allow_unicode=True, width=120)

    print(f"Generated: {output_file}")