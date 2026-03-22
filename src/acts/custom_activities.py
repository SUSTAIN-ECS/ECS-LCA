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
    ret = []
    for activity in activities:
        # Create new custom activity
        act = agb.newActivity(
            foreground_db,
            activity['id'],
            amount= activity["output"]["amount"]["value"],
            unit = activity["output"]["amount"]["unit"],
            exchanges={}
        )
        ret.append((act,activity.get("inputs", [])))
    return ret

def add_all_exchanges(all_acts, foreground_db):
    for act, input_data in all_acts:
        exchanges = {}

        for input_name, input_value in input_data.items():
            param_name = f"{act['name']}_{input_name}".replace(" ", "_")

            child_act, param = input_to_activity(param_name, input_value, foreground_db)
            #Need to do the get in case where multiple inputs link to the same activity
            exchanges[child_act] =  exchanges.get(child_act,0) + param

        act.addExchanges(exchanges)

def generate_activities(path, db):
    custom_activities = load_custom_activities(path)
    acts = create_custom_activities(custom_activities, foreground_db=db)
    add_all_exchanges(acts, foreground_db=db)
