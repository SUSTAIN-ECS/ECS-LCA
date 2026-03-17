import lca_algebraic as agb
import brightway2 as bw
import yaml as yml
import os
import hashlib

def find_activity(activity_name, location, custom_db):
    """
    Finds activities in the ecoinvent database or in the foreground DB.
    The latter contains either (1) custom activities or (2) modified ecoinvent activities.
    """

    try:
        return agb.findActivity(activity_name, db_name=custom_db)
    except Exception as e:
        pass
    try:
        return agb.findBioAct(activity_name)
    except Exception as e:
        pass

    return agb.findTechAct(activity_name, loc=location)

def get_param_type(value):
    if isinstance(value, bool):
        return "boolean"
    elif isinstance(value, float):
        return "float"
    elif isinstance(value, int):
        return "float"
    elif isinstance(value, str):
        return "enum"
    else:
        raise ValueError(f"Unsupported type: {typenum_capa(value)}")

def get_param(name,row):
    """
    Create the parameters in the lca algebraic framework for one of the excel sheet.

    params_df: the dataframe that has been created for one excel sheet
    parameter_registryMa théorie c'est: the register of parameter
    sheet_name: the name of the excel sheet params_df
    """
    amount = row["amount"]
    param_type = get_param_type(amount["typical"]).strip().lower()
    param_name = f"{name}_{amount['unit'].translate(str.maketrans({'²': '2','³': '3'}))}"
    try:
        if param_type == "float":
            unc = amount.get("uncertainty",{})

            if "distribution" not in unc:
                return agb.unit_registry.Quantity(amount["typical"], amount['unit'])

            distrib = unc.get("distribution", "FIXED").upper()
            return agb.newFloatParam(
                param_name,
                default=amount["typical"],
                unit=amount["unit"],
                min=unc.get("min"),
                max=unc.get("max"),
                std=unc.get("std"),
                distrib=getattr(agb.DistributionType, distrib, None),
                description=row.get("Description"),
                label=row.get("Label")
            )
        elif param_type == "bool":
            return agb.newBoolParam(
                param_name,
                default=row["output"]["value"]
            )
        elif param_type == "enum":
            values = eval(row["Values"]) if isinstance(row["Values"], str) else row["Values"]
            weights = eval(row["Weights"]) if isinstance(row["Weights"], str) else None

            if weights:
                values = {k: v for k, v in zip(values, weights)}

            return agb.newEnumParam(
                param_name,
                values=values,
                default=row["Default"],
                description=row.get("Description")
            )
        else:
            raise ValueError(f"Unsupported parameter type: {param_type}")
        
    except Exception as e:
        print(f"Error creating parameter '{param_name}': {e}")

def export_all_db_as_enum(path):
    all_names = sorted({key['name'] for db_name in bw.databases for key in bw.Database(db_name)})

    with open(path, "w", encoding="utf-8") as f:
        yml.dump({"enum": all_names}, f, allow_unicode=True, sort_keys=False)

import hashlib

def folder_changed(folder: str, state_file: str) -> bool:
    """
    Return True if the folder has changed since last run.
    Always updates the saved folder hash.
    Only saves a single hash of the folder.
    """
    def hash_file(path: str) -> str:
        """Compute SHA256 hash of a file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    # Build a deterministic combined hash of all files
    hashes = []
    for root, dirs, files in os.walk(folder):
        for name in sorted(files):
            path = os.path.join(root, name)
            rel_path = os.path.relpath(path, folder)
            file_hash = hash_file(path)
            hashes.append(f"{rel_path}:{file_hash}")

    # Combine all file hashes into a single folder hash
    folder_hash = hashlib.sha256("\n".join(sorted(hashes)).encode()).hexdigest()

    # Load previous hash
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            prev_hash = f.read().strip()
    else:
        prev_hash = None

    # Always update saved hash
    os.makedirs(os.path.dirname(state_file) or ".", exist_ok=True)
    with open(state_file, "w") as f:
        f.write(folder_hash)

    return prev_hash != folder_hash