import lca_algebraic as agb
from pathlib import Path
import yaml as yml

from src.utils.utils import get_param, find_activity

def process_fground(fground, OS_database, name):
    ret = {}

    if "inputs" in fground:
        fground = fground["inputs"]

    for input_name, row in fground.items():
        new_activity_name = f"_{name}_{input_name}"
        param = get_param(new_activity_name, row)

        location = row.get("location", "GLO")

        activity = find_activity(row["act_name"],location,OS_database)

        if activity is None:
            print(f"Skipping creation of {new_activity_name} due to unresolved activity issues.")
            continue

        try:
            exchanges = {activity: param}  # Define exchanges
        except Exception as e:
            print(f"Error in parameter expression for activity '{new_activity_name}': {e}")
            continue

        try:
            act = agb.newActivity(OS_database, new_activity_name, "unit", exchanges=exchanges, act_id_name = new_activity_name)
            for i in row:
                if i[:2] == "c_":
                    act.updateMeta(**{str(i): str(row[i])})

            ret[act]=1
        except Exception as e:
            print(f"Error creating activity '{new_activity_name}': {e}")
    return ret

def get_reference_flow(path, db):

    with open(path, "r") as f:
        fground = yml.safe_load(f)

    exchanges_foreground = process_fground(fground, db, Path(path).stem)

    return agb.newActivity(db,f"act_{path}",  "unit", exchanges=exchanges_foreground) # Create the foreground

