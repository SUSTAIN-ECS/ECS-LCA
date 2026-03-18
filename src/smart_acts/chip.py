import lca_algebraic as agb
from src.utils.utils import unit_trans

def die_area_pred(package_data):
    # Return predicted die area in mm² based on package size. 

    p_area = package_data["area"]["value"] 
    p_area *= unit_trans(package_data["area"]["unit"], "mm²")
    

    if package_data["type"] == "BGA":
        return 0.822*p_area**0.73
    if package_data["type"] == "WLP":
        return 0.759*p_area**0.99
    if package_data["type"] == "SOP":
        return 0.063*p_area**1.1
    if package_data["type"] in ["QFN","DFN"]:
        return 0.214*p_area**0.99
    if package_data["type"] == "QFP":
        return 0.724*p_area**0.6
    raise Exception("Package type not supported")

def chip_smart_activity(activity):
    data = activity["data"]
    die_area = data.get("die", {}).get("area", None)
    if die_area == None:
        package_data = data.get("package", None)
        if package_data == None:
            Exception(f"Not enough data to predict impact of chip {activity['id']}")
        die_area = {"value": die_area_pred(package_data), "unit": "mm²"}
    
    f = 1/180 if data['type'] == "logic" else 1/191 # kg/cm²

    
    activity["act_name"] = f"market for integrated circuit, {data['type']} type"
    activity["amount"]= {
                "typical": die_area["value"] * unit_trans(die_area["unit"], "cm²") * f,
                "unit": "kg"
            }
    return activity
