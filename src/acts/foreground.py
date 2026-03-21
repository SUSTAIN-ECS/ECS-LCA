import lca_algebraic as agb
from pathlib import Path
import yaml as yml

from src.acts.custom_activities import input_to_activity
from src.smart_acts import smart_activity
from src.utils.utils import get_param, find_activity

def process_fground(fground, foreground_db, name):
    ret = {}

    if "inputs" in fground:
        fground = fground["inputs"]

    for input_name, input_value in fground.items():

        new_activity_name = f"_{name}_{input_name}"
        activity, param = input_to_activity(new_activity_name, input_value, foreground_db)

        try:
            act = agb.newActivity(foreground_db, 
                                  new_activity_name,
                                  "unit",
                                  exchanges={activity:param},
                                  act_id_name = new_activity_name)
            for i in input_value:
                if i[:2] == "c_":
                    act.updateMeta(**{str(i): str(input_value[i])})

            ret[act]=1
        except Exception as e:
            print(f"Error creating activity '{new_activity_name}': {e}")
    return ret

def get_reference_flow(path, db):

    with open(path, "r") as f:
        fground = yml.safe_load(f)

    exchanges_foreground = process_fground(fground, db, Path(path).stem)

    return agb.newActivity(db,f"act_{Path(path).stem}",  "unit", exchanges=exchanges_foreground) # Create the foreground

