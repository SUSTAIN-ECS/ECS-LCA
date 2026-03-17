def die_area_pred(package_data):
    #supposes package in mm2, should translate to be robost
    p_area = package_data["area"]["value"]
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
    die_area = activity["data"].get("die", {}).get("area", None)
    if die_area == None:
        package_data = activity["data"].get("package", None)
        if package_data == None:
            Exception(f"Not enough data to predict impact of chip {activity['id']}")
        die_area = {"value": die_area_pred(package_data), "unit": "mm²"}
    activity["act_name"] = "market for wafer, fabricated, for integrated circuit"
    activity["amount"]= {
                "typical": die_area["value"],
                "unit": die_area["unit"]
            }
    return activity
