import lca_algebraic as agb
import pandas as pd


def find_activity(ei_activity_name, location, custom_process_name, modified_activity_name, custom_db):
    """
    Finds activities in the ecoinvent database or in the foreground DB.
    The latter contains either (1) custom activities or (2) modified ecoinvent activities.
    """
    if pd.notna(modified_activity_name): # Check for the modified activities first
        try:
            modified_activity = agb.findActivity(modified_activity_name, db_name=custom_db)
            return modified_activity
        except Exception as e:
            print(f"Failed to find activity '{modified_activity_name}' in custom database '{custom_db}': {e}")

    if pd.notna(custom_process_name): # Check for the custom activity
        try:
            custom_process = agb.findActivity(custom_process_name, db_name=custom_db)
            return custom_process
        except Exception as e:
            print(f"Failed to find custom process '{custom_process_name}' in custom database '{custom_db}': {e}")

    try: # Fallback to the native Ecoinvent database, if the activity is not custom or modified
        if pd.notna(location):  # If location is provided
            return agb.findTechAct(ei_activity_name, loc=location)
        else:
            return agb.findTechAct(ei_activity_name)
    except Exception as e:
        print(f"Failed to find activity '{ei_activity_name}' in Ecoinvent for location '{location}': {e}")
        return None



def process_parameters(params_df, parameter_registry,sheet_name):
    """
    Create the parameters in the lca algebraic framework for one of the excel sheet.

    params_df: the dataframe that has been created for one excel sheet
    parameter_registry: the register of parameter
    sheet_name: the name of the excel sheet params_df
    """
    params_df["Type"] = params_df["Type"].astype(str).str.strip().str.lower()

    for index, row in params_df.iterrows():
        param_name = str(sheet_name)+"_"+str(row["parameter number"])
        param_type = row["Type"].strip().lower()

        if pd.isna(row["EI activity name"]):
            print(f"Skipping row {index} as 'EI activity name' is NaN.")
            break

        try:
            if param_type == "float":
                param = agb.newFloatParam(
                    param_name,
                    default=row["Default"],
                    min=row.get("Min"),
                    max=row.get("Max"),
                    std=row.get("Std"),
                    distrib=getattr(agb.DistributionType, row["Distrib"].upper(), None),
                    description=row.get("Description"),
                    label=row.get("Label")
                )
            elif param_type == "bool":
                param = agb.newBoolParam(
                    param_name,
                    default=row["Default"]
                )
            elif param_type == "enum":
                values = eval(row["Values"]) if isinstance(row["Values"], str) else row["Values"]
                weights = eval(row["Weights"]) if isinstance(row["Weights"], str) else None

                if weights:
                    values = {k: v for k, v in zip(values, weights)}

                param = agb.newEnumParam(
                    param_name,
                    values=values,
                    default=row["Default"],
                    description=row.get("Description")
                )
            else:
                raise ValueError(f"Unsupported parameter type: {param_type}")

            # Register the parameter for later evaluation
            parameter_registry[param_name] = param
            print(f"Parameter created and registered: {param_name}") # for debugging only !
        except Exception as e:
            print(f"Error creating parameter '{param_name}': {e}")



def create_custom_activities(custom_meta_data_DF,OS_database_dataframes,OS_database,parameter_registry):
    """
    The aim here is to create activities that don't exist in Ecoinvent. They are custom or modified activities.
    Note: at the end of the day, they are still built from different activities that exist in the ecoinvent database.
    """
    sorted_sheets = (
        custom_meta_data_DF
        .sort_values(by="priority")         # smallest priority first
        .index
        .tolist()
    )

    for sheet_name in sorted_sheets: # iterate in the custom sheets
        sheet_df=OS_database_dataframes[sheet_name]
        if custom_meta_data_DF.loc[sheet_name]["type"] == "custom":
            sheet_location=custom_meta_data_DF.loc[sheet_name]["location"]
            sheet_unit=custom_meta_data_DF.loc[sheet_name]["unit"]
            print(f"Processing sheet: {sheet_name}") # to keep track of which sheet is been processed
            accumulated_exchanges = {}

            for index, row in sheet_df.iterrows():         # iterate inside a given custom sheet
                ei_activity_name = row["EI activity name"] # get the name of the ei activity at a given row
                if pd.isna(ei_activity_name):              # Break when 'EI activity name' is NaN, -> when we're at the end of the i-th custom sheet
                    print(f"Skipping row {index} in sheet '{sheet_name}' as 'EI activity name' is NaN.")
                    break

                location = row["loc"]
                parameter_expression = str(sheet_name)+"_"+str(row["parameter number"])
                new_activity_name = row["LCA algebraic name"]
                custom_process_name = row["Custom process name"]
                modified_activity_name = row["Modified process name"]

                # Let's find the activity, either custom, modified or already present in ecoinvent
                ei_activity = find_activity(ei_activity_name, location,
                                            custom_process_name = custom_process_name,
                                            modified_activity_name = modified_activity_name,
                                            custom_db=OS_database)


                if ei_activity is None:
                    print(f"Skipping row {index} in sheet '{sheet_name}' due to unresolved activity issues.") # if the activity is not found, should not happen !
                    continue

                try: # We also need to associate exchanges inside custom activities with parameter values
                    parameter_value = eval(parameter_expression, {}, parameter_registry) # evaluate the parameter expression
                    if ei_activity in accumulated_exchanges:
                        accumulated_exchanges[ei_activity] += parameter_value  # accumulate value if activity already exists
                    else:
                        accumulated_exchanges[ei_activity] = parameter_value  # add new activity to exchanges
                except Exception as e:
                    print(f"Error in parameter expression for activity in row {index}: {e}")
                    continue

            try:
                agb.newActivity(OS_database, sheet_name, sheet_unit, exchanges=accumulated_exchanges) # Create the custom process with accumulated exchanges and associated parameters

            except Exception as e:
                print(f"Error creating custom activity '{sheet_name}': {e} \n") # Should not happen !

        if custom_meta_data_DF.loc[sheet_name]["type"] == "modified":
            original_EI_activity_name=custom_meta_data_DF.loc[sheet_name]["original EI activity name"]
            original_EI_activity_location=custom_meta_data_DF.loc[sheet_name]["original EI activity location"]
            sheet_location=custom_meta_data_DF.loc[sheet_name]["location"]
            sheet_unit=custom_meta_data_DF.loc[sheet_name]["unit"]
            modified_activity_name=sheet_name
            try:
                original_activity = agb.findTechAct(original_EI_activity_name, loc=original_EI_activity_location)
                if original_activity is None:
                    print(f"Skipping copy and update for {modified_activity_name} due to unresolved activity issues.")
                    continue

                new_activity = agb.copyActivity(OS_database, original_activity, modified_activity_name)  # Create a copy of the activity
                print(f"Copied activity: {modified_activity_name}")

                sheet_data = OS_database_dataframes[modified_activity_name]
                exchanges_dict = {}

                # TBM = To Be Modified inside the copied activity
                for idx, sheet_row in sheet_data.iterrows():
                    ei_activity_name_TBM = sheet_row["EI activity name"]
                    parameter_expression_TBM = str(modified_activity_name)+"_"+str(sheet_row["parameter number"])

                    try:
                        amount = eval(parameter_expression_TBM, {}, parameter_registry)  # Evaluate the parameter expression to get the amount
                        print(f"Evaluated amount for '{ei_activity_name_TBM}': {amount}")
                        exchanges_dict[ei_activity_name_TBM] = dict(amount=amount)  # Structure the exchange as a dictionary with amount
                    except Exception as e:
                        print(f"Error evaluating parameter expression '{parameter_expression_TBM}' for activity '{ei_activity_name_TBM}': {e}")
                        continue  # Skip this exchange if there's an error

                try:  # Now, update exchanges for the new activity
                    new_activity.updateExchanges(exchanges_dict)
                    print(f"Updated exchanges for activity: {modified_activity_name}")

                except Exception as e:
                    print(f"Error updating exchanges for activity '{modified_activity_name}': {e}")
                    continue
            except Exception as e:
                print(f"Error in copying or updating activity '{modified_activity_name}': {e}")


    print("Finished processing all sheets.")

def create_foreground(foregrounds_All,selected_foreground,OS_database,parameter_registry):
    for index, row in foregrounds_All[f"{selected_foreground}"].iterrows():          # Iterate through the rows of the foreground sheet and create new activities

        ei_activity_name = row["EI activity name"]       # Read values from the Excel file
        location = row["loc"]                            # Location (optional)
        new_activity_name = row["LCA algebraic name"]    # the name of the new activity is defined in "LCA algebraic name"
        parameter_expression = str(selected_foreground)+"_"+str(row["parameter number"])          # Name of the associated parameter
        modified_activity_name = row["Modified process name"]         # name of the modified activity (if relevant)
        custom_process_name = row["Custom process name"] # name of the custom activity (if relevant)

        if pd.isna(ei_activity_name):  # Stop processing when 'EI activity name' is NaN
            print(f"Stopping processing at index {index} as 'EI activity name' is NaN.")
            break  # Exit the loop

        else:
            ei_activity = find_activity(ei_activity_name, location,
                                        custom_process_name = custom_process_name,
                                        modified_activity_name = modified_activity_name,
                                        custom_db=OS_database) # Let's find the activity, either custom, modified or already present in ecoinvent

            if ei_activity is None:
                print(f"Skipping creation of {new_activity_name} due to unresolved activity issues.")
                continue

            try:
                exchanges = {ei_activity: eval(parameter_expression, {}, parameter_registry)}  # Define exchanges
            except Exception as e:
                print(f"Error in parameter expression for activity '{new_activity_name}': {e}")
                continue

            try:
                agb.newActivity(OS_database, new_activity_name, "unit", exchanges=exchanges)
                print(f"Activity created: {new_activity_name}")
            except Exception as e:
                print(f"Error creating activity '{new_activity_name}': {e}")
