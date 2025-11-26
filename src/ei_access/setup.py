import brightway2 as bw
import bw2io

def setup_database(eia, project_name):
    if any('ecoinvent' in key for key in bw.databases.keys()):
        print("Initial setup already done, skipping")
        return

    if eia.path != None and eia.name != None:
        ei39cut = bw.SingleOutputEcospold2Importer(eia.path, eia.name)
        ei39cut.apply_strategies()
        ei39cut.statistics()
        ei39cut.write_database()    
        return

    if eia.username != None and eia.password:
        # Download the dabase    
        bw2io.import_ecoinvent_release(version = "3.9.1",
                                       system_model = "cutoff",
                                       username = eia.username,
                                       password = eia.password,
                                   ) 
        return
    raise ValueError(f"Please fill EcoInvent database access mean")
