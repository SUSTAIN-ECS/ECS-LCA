from src.acts.composite_activities import composite_activity
from src.utils.utils import find_activity, get_param
from src.smart_acts import smart_activity

from pathlib import Path
import lca_algebraic as agb
import yaml

def load_custom_activities(yaml_path):
    activities = []

    for file in Path(yaml_path).rglob("*.yaml"):
        with open(file, "r") as f:
            data = yaml.safe_load(f)
            if data == None:
                continue
            data["id"] = str(file.stem)
            activities.append(data)

    return activities

def order_activities(acts):
    node_map = {n["id"]: n for n in acts}
    present = set(node_map.keys())

    visited = set()
    result = []

    def dfs(node):
        if node["id"] in visited:
            return

        visited.add(node["id"])

        for child in node["inputs"].values():
            if "act_name" not in child:
                #Smart activities can only link to ecoinvent at the moment
                #Should be fixed if smart activities are extended further
                continue
            child_id = child["act_name"]
            if child_id in present:
                dfs(node_map[child_id])

        result.append(node)

    for act in acts:
        dfs(act)

    return result

def input_to_activity(param_name, input_value, db):
    if "type" in input_value:
        input_value = smart_activity(input_value)

    if "composition" in input_value:
        return composite_activity(param_name, input_value, db)
    
    param = get_param(param_name, input_value)

    # Resolve mapping
    ei_name = input_value["act_name"]
    location = input_value.get("location", "GLO")

    # Find background activity
    activity = find_activity(ei_name, location, db)

    if activity is None:
        raise ValueError(
            f"Background activity not found: {ei_name} ({location})"
        )
    return activity, param

def create_custom_activities(activities, foreground_db):
    for activity in activities:
        unit = activity["output"]["amount"]["unit"]
        exchanges = {}

        for input_name, input_value in activity.get("inputs", []).items():
            param_name = f"{activity['id']}_{input_name}"

            child_act, param = input_to_activity(param_name, input_value, foreground_db)
            #Need to do the get in case where multiple inputs link to the same activity
            exchanges[child_act] =  exchanges.get(child_act,0) + param

        # Create new custom activity
        agb.newActivity(
            foreground_db,
            activity['id'],
            unit,
            exchanges=exchanges
        )

def generate_activities(path, db):
    custom_activities = load_custom_activities(path)
    custom_activities = order_activities(custom_activities)
    create_custom_activities(custom_activities, foreground_db=db)
