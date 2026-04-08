import lca_algebraic as agb
from src.utils.utils import unit_trans

def die_area_pred(package_data):
    # Return predicted die area in mm² based on package size. 
    # https://anncollin.github.io/DieAreaPrediction/

    param_die_pred = {
        "BGA": (0.822, 0.73),
        "WLP": (0.759, 0.99),
        "SOP": (0.063, 1.1),
        "QFN": (0.214, 0.99),
        "DFN": (0.214, 0.99),
        "QFP": (0.724, 0.6)
    }

    p_area = package_data["area"]["value"] 
    p_area *= unit_trans(package_data["area"]["unit"], "mm²")
    
    if package_data["type"] not in param_die_pred:
        raise Exception(f"Package type {package_data['type']} not supported")

    a, beta = param_die_pred[package_data["type"]]
    return a*p_area**beta

def pack_weight_pred(data):
    # Temporary factor from Augustin Wattiez based on OSSDA dataset
    # waiting for more complete and precise measurements

    param_pack_weight = {
        "BGA": 2.93,
        "WLP": 1.11,
        "DFN": 4.07,
        "QFN": 4.07,
        "SOP": 5.60,
        "QFP": 4.49,
    }

    d_area = data["package"]["area"]["value"] 
    d_area *= unit_trans(data["package"]["area"]["unit"], "mm²")
    p_type = data['package']['type']

    if p_type not in param_pack_weight:
        raise Exception(f"Package type {p_type} not supported")

    return d_area * param_pack_weight[p_type]

def waf_elec_int(data):
    # Based on
    # returns factor in kWh/cm² of wafer
    param_type_int = {
        # Boakes, Lizzie, et al. "Cradle-to-gate life cycle assessment of CMOS logic technologies." 2023
        "A14": 4.10,
        "N2": 3.75,
        "N3": 3.77,
        "N5": 3.18,
        "N7 EUV": 2.72,
        "N7": 2.77,
        "N10": 2.09,
        "N14": 1.83,
        "N20": 1.73,
        "N28": 1.56,
        # Boyd, S. B. (2011). Life-cycle assessment of semiconductors. Springer Science & Business Media.
        "N45": 1.4 / 1.11,
        "N65": 1.5 / 1.4,
        "N90": 1.5 / 1.4,
        "N130": 1.5 / 1.4,
        "N180": 1.6 / 1.25,
        "N250": 1.6 / 1.5,
        "N350": 1.8 / 1.96,

    }

    if "technology" not in data["die"]:
        return 2.76 #Ecoinvent default value

    d_tech = data["die"]["technology"]
    if d_tech not in param_type_int:
        print(f"Package type {d_tech} not supported, using default Ecoinvent value")
        return 2.76

    return param_type_int[d_tech]

def chip_smart_activity(activity):
    data = activity["data"]
    ret = {}

    die_area = data.get("die", {}).get("area", None)
    pack_weight = data.get("package", {}).get("weight", None)

    if die_area == None:
        die_area = {"value": die_area_pred(data.get("package", None)), "unit": "mm²"}
        data["die"] = data.get("die", {})
        data["die"]["area"] = die_area

    if pack_weight == None:
        pack_weight =  {"value": pack_weight_pred(data), "unit": "mg"}
        data["package"] = data.get("package", {})
        data["package"]["weight"] = pack_weight

    n_chips = data.get("amount", 1)

    wafer_activity = {}
    wafer_activity["act_name"] = f"mod_waf"
    wafer_activity["amount"]= {
        "value": die_area["value"] * n_chips,
        "unit": die_area["unit"]
        }
    ret["wafer"] = wafer_activity

    package_activity = {}
    package_activity["act_name"] = f"market_circ_logic_no_waf"
    package_activity["amount"]= {
        "value": pack_weight["value"] * n_chips,
        "unit": pack_weight["unit"]
        }
    ret["package"] = package_activity

    elec_activity = {}
    elec_activity["act_name"] = f"market group for electricity, medium voltage"
    elec_activity["amount"]= {
        "value": die_area["value"] * unit_trans(die_area["unit"], "cm²") * waf_elec_int(data) * n_chips,
        "unit": "kWh"
        }
    ret["elec"] = elec_activity

    return ret
