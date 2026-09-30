import json

project_name = "Physics Research Agent"

research_topics = [
    "micromagnetics",
    "MuMax3",
    "COMSOL",
    "Vampire",
]

research_task = {
    "question": "Compare MuMax3 and COMSOL simulation results",
    "status": "learning",
    "day": 1,
}

print("Project:", project_name)
print("Topics:", research_topics)

print("\nPython dictionary:")
print(research_task)

json_text = json.dumps(
    research_task,
    indent=2,
    ensure_ascii=False
)

print("\nJSON:")
print(json_text)