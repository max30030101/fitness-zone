"""Workout library: ready-made sessions people can follow and mark as complete.
Completing one writes a real WorkoutLog row, so dashboard numbers only ever reflect what the user did."""

LEVELS = [("beginner", "Beginner"), ("intermediate", "Intermediate"), ("advanced", "Advanced")]
GOALS = [("build_muscle", "Build muscle"), ("lose_fat", "Lose fat"), ("strength", "Get stronger"),
         ("endurance", "Boost endurance"), ("general", "General fitness")]
EQUIPMENT = [("none", "No equipment"), ("home", "Home (dumbbells, bands)"), ("gym", "Full gym")]
DURATIONS = [(20, "Up to 20 min"), (30, "Up to 30 min"), (45, "Up to 45 min"), (60, "Up to 60 min")]


def _w(slug, title, level, goal, duration, equipment, summary, exercises):
    return {
        "slug": slug, "title": title, "level": level, "goal": goal, "duration": duration, "equipment": equipment,
        "summary": summary,
        "exercises": [dict(name=n, sets=s, reps=r, rest=rest, cue=c) for n, s, r, rest, c in exercises],
        "level_label": dict(LEVELS)[level], "goal_label": dict(GOALS)[goal], "equipment_label": dict(EQUIPMENT)[equipment],
    }


WORKOUTS = [
    _w("first-steps-full-body", "First Steps Full Body", "beginner", "general", 20, "none",
       "A gentle full-body session that needs only floor space. A good place to start or restart.", [
           ("Bodyweight squat", 3, "10", 45, "Sit back and down, drive through your heels."),
           ("Incline push-up", 3, "8", 45, "Hands on a sturdy table or bench, body in one line."),
           ("Glute bridge", 3, "12", 45, "Press your hips up and squeeze at the top."),
           ("Dead bug", 3, "8 each side", 45, "Keep your lower back on the floor as you reach."),
           ("Plank", 3, "20 sec", 45, "Forearms down, breathe steadily."),
       ]),
    _w("starter-cardio-burn", "Starter Cardio Burn", "beginner", "lose_fat", 25, "none",
       "Low-impact intervals that raise your heart rate without equipment. Take extra rest whenever you need it.", [
           ("Jumping jacks", 3, "30 sec", 30, "Easy rhythm, land softly."),
           ("Reverse lunge", 3, "8 each leg", 40, "Step back, lower with control."),
           ("High knees", 3, "30 sec", 30, "Pump your arms, drive your knees up."),
           ("Bicycle crunch", 3, "12", 40, "Slow and controlled, opposite elbow to knee."),
           ("Wall angel", 2, "10", 30, "Keep your back against the wall as your arms slide."),
       ]),
    _w("dumbbell-basics-home", "Dumbbell Basics at Home", "beginner", "build_muscle", 30, "home",
       "Five classic moves with one pair of dumbbells. Choose a weight that feels challenging by the last rep.", [
           ("Goblet squat", 3, "10", 60, "Hold one dumbbell at your chest and squat deep."),
           ("Dumbbell floor press", 3, "10", 60, "Lie on the floor, press up, lower until your elbows touch down."),
           ("One-arm dumbbell row", 3, "10 each arm", 60, "Pull the dumbbell to your hip."),
           ("Dumbbell shoulder press", 3, "8", 60, "Ribs down, press straight overhead."),
           ("Hammer curl", 2, "12", 45, "Elbows by your sides, no swinging."),
       ]),
    _w("upper-body-builder", "Upper Body Builder", "intermediate", "build_muscle", 40, "gym",
       "A gym session for chest, back, shoulders and arms with steady, controlled reps.", [
           ("Barbell bench press", 4, "8", 90, "Shoulder blades pinched, bar to mid-chest."),
           ("Lat pulldown", 4, "10", 75, "Pull to your upper chest, elbows down and back."),
           ("Dumbbell shoulder press", 3, "10", 75, "Press overhead without arching your back."),
           ("Seated cable row", 3, "12", 60, "Sit tall and avoid swinging."),
           ("Cable triceps pushdown", 3, "12", 45, "Elbows by your sides, squeeze at the bottom."),
       ]),
    _w("home-conditioning-circuit", "Home Conditioning Circuit", "intermediate", "endurance", 30, "none",
       "Four rounds of simple moves that build stamina. Scale any exercise down if form slips.", [
           ("Burpees", 4, "10", 40, "Step back instead of jumping if you need to."),
           ("Mountain climbers", 4, "30 sec", 30, "Run your knees toward your chest."),
           ("Jump squat", 4, "12", 40, "Land softly with bent knees."),
           ("Push-up", 4, "12", 40, "Drop to your knees if you can't hold form."),
           ("Plank", 3, "45 sec", 30, "Squeeze your glutes and breathe."),
       ]),
    _w("strength-foundations", "Strength Foundations", "intermediate", "strength", 45, "gym",
       "Heavier sets of fewer reps on core lifts. Rest fully and keep your technique clean.", [
           ("Barbell back squat", 5, "5", 150, "Brace your core, squat to parallel or lower."),
           ("Barbell overhead press", 5, "5", 120, "Squeeze your glutes, press in a straight line."),
           ("Barbell bent-over row", 4, "6", 120, "Hinge at the hips, keep your back flat."),
           ("Dumbbell Romanian deadlift", 3, "8", 90, "Soft knees, push your hips back."),
           ("Hanging knee raise", 3, "10", 60, "Lift without swinging."),
       ]),
    _w("push-pull-power", "Push-Pull Power", "advanced", "build_muscle", 50, "gym",
       "A demanding upper-body session pairing pushing and pulling movements.", [
           ("Pull-up", 4, "6-8", 120, "Full hang to chin over the bar."),
           ("Barbell bench press", 4, "6", 120, "Control the lowering phase."),
           ("Barbell bent-over row", 4, "8", 90, "Row to your lower ribs."),
           ("Cable face pull", 3, "15", 60, "Elbows high, squeeze the rear shoulders."),
           ("Barbell curl", 3, "10", 60, "Strict reps, no body swing."),
       ]),
    _w("heavy-lower-day", "Heavy Lower Day", "advanced", "strength", 60, "gym",
       "Heavy squats and deadlifts followed by accessory work. Only for people with solid technique.", [
           ("Barbell back squat", 5, "4", 180, "Stay tight through the whole rep."),
           ("Conventional deadlift", 4, "4", 180, "Bar over mid-foot, flat back, push the floor away."),
           ("Leg press", 3, "10", 90, "Controlled depth, don't lock out hard."),
           ("Leg curl machine", 3, "12", 60, "Pause at the top, lower slowly."),
           ("Cable crunch", 3, "12", 45, "Curl your ribs toward your pelvis."),
       ]),
    _w("engine-builder", "Engine Builder", "advanced", "endurance", 45, "gym",
       "Machine intervals and bodyweight finishers to build stamina. Pace the early rounds.", [
           ("Rowing machine intervals", 6, "2 min hard", 60, "Legs, then body, then arms."),
           ("Stationary bike intervals", 5, "3 min", 60, "Steady hard effort, then recover."),
           ("Burpees", 3, "12", 45, "Keep a rhythm you can sustain."),
           ("Skipping rope", 4, "60 sec", 30, "Light bounces on the balls of your feet."),
           ("Plank", 3, "60 sec", 30, "Keep your hips level."),
       ]),
]


def get_workout(slug):
    return next((w for w in WORKOUTS if w["slug"] == slug), None)


def featured_workouts():
    """One session per level, for the home page."""
    chosen = []
    for level, _ in LEVELS:
        chosen.append(next(w for w in WORKOUTS if w["level"] == level))
    return chosen


def filter_workouts(params):
    level, goal, equip = params.get("level", ""), params.get("goal", ""), params.get("equipment", "")
    try:
        max_minutes = int(params.get("duration", "") or 0)
    except ValueError:
        max_minutes = 0
    result = []
    for w in WORKOUTS:
        if level and w["level"] != level: continue
        if goal and w["goal"] != goal: continue
        if equip and w["equipment"] != equip: continue
        if max_minutes and w["duration"] > max_minutes: continue
        result.append(w)
    return result
