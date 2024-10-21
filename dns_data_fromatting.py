import pandas as pd
import json
import re

"""
PLEASE CONFIGURE BELOW FLAG BEFORE RUNNING THE CODE, 
Keep the value for both flag as False in case you want to hard code input data
"""
single_input = False
multipleInput = True

# Please enable any one environment only
dns_details_env = "-dev"
# dns_details_env = "-prod"
# dns_details_env = "-stage"


# mention your DNS file path here
dns_detail_file_path_inp = r"C:\Users\mwashidhusain\Documents\projects\python_practice\soumya\Details of DNS.xlsx"
# read user input
single_input_file_path = (
    r"C:\Users\mwashidhusain\Documents\projects\python_practice\soumya\user_input.txt"
)

multiple_Input_file_path = r"C:\Users\mwashidhusain\Documents\projects\python_practice\soumya\refence file 1.txt"


# Zone map
zone_map = {
    "eu-west-1": "euw1",
    "eu-west-2": "euw2",
    "us-east-1": "use1",
    "us-east-2": "use2",
    "ap-southeast-2": "apse2",
}


def get_dns_details_list(dns_detail_file_path_inp):
    # get dns details as dataframe
    dns_df = pd.read_excel(dns_detail_file_path_inp, header=None)
    resource_record_df = dns_df.iloc[9:, [2]]
    resource_record_df = pd.DataFrame(
        resource_record_df.values[1:], columns=[resource_record_df.values[0]]
    )
    resource_record_list = resource_record_df.values.ravel().tolist()
    return resource_record_list


def convert_string_to_dict(user_input):
    print("Converting String to Dict")
    result = {}
    for line in user_input.strip().splitlines():
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"')
        if val.startswith("[") and val.endswith("]"):
            val = eval(val)
        result[key] = val

    return result


def get_zone_id_value(records):
    print(f"Getting zone id value for {records}")

    result_string = ""
    try:
        records = records[0].split(".")
        if records[-3] == "elb":
            result_string = "alb."
        result_string = f"{result_string}{zone_map.get(records[-4],"")}"
    except Exception as e:
        print(f"Error : {e}")

    return result_string


def format_user_input(user_input_dict):
    print("Formatting user input for name :", user_input_dict["name"])
    result_output_dict = {}

    if any(
    user_input_dict["name"] in item and dns_details_env in user_input_dict["name"]
    for item in get_dns_details_list(dns_detail_file_path_inp)
    ):
        result_output_dict = {
            "name": " ",
            "type": "",
            "alias": {"name": "", "zone_id": "", "evaluate_target_health": "false"},
        }

        result_output_dict["name"] = user_input_dict["name"]

        if user_input_dict["type"] == "CNAME":
            result_output_dict["type"] = "A"
        else:
            print(
                f"for input data: {user_input_dict}\nHere type is not 'CNAME'. So skipping this input data."
            )
            return {}
        result_output_dict["alias"]["name"] = user_input_dict["records"]
        result_output_dict["alias"][
            "zone_id"
        ] = f"module.r53_zone_ids.{get_zone_id_value(user_input_dict["records"])}"
        return result_output_dict

    else:
        print("DNS details did not matched with provided input data")
        return {}


# This function do prepare the actual formatted with data manipulation
def format_dict(result_output_dict, indent_level=0):

    indent = "    " * indent_level

    if isinstance(result_output_dict, dict):
        formatted_items = []
        for key, value in result_output_dict.items():
            if key == "alias" and isinstance(value, dict):
                if "name" in value and isinstance(value["name"], list):
                    # Convert list to string
                    names = ", ".join(value.pop("name"))
                    value = {'temp_name': names, **value}

                formatted_items.append(
                    f"{indent}{key} = {format_dict(value, indent_level + 1)}"
                )

            else:

                if key in ["temp_name"]:
                    formatted_items.append(f"{indent}{"name"}                   = {value}")
                elif key in ["zone_id"]:
                    formatted_items.append(f"{indent}{key}                = {value}")
                elif key in ["evaluate_target_health"]:
                    formatted_items.append(f"{indent}{key} = {value}")

                else:
                    formatted_items.append(f'{indent}{key} = "{value}"')

        return "{\n" + "\n".join(formatted_items) + f"\n{indent}}}"
    else:
        return str(result_output_dict)


def parse_input_data(text_data):
    # This function process large unstructured data to get the records section data in dictionary format.

    json_output = {}
    # Step 1: Remove &nbsp; and other unnecessary characters
    cleaned_text = text_data.replace("&nbsp;", " ")

    # Step 2: Normalize whitespace
    normalized_text = re.sub(r"\s+", " ", cleaned_text)

    # Step 3: Extract the records section
    records_section_match = re.search(
        r"records\s*=\s*\[(.*)\]", normalized_text, re.DOTALL
    )
    if records_section_match:
        records_section = records_section_match.group(1)

        # Step 4: Parse each record
        record_pattern = re.compile(
            r'\{\s*name\s*=\s*"(.*?)"\s*type\s*=\s*"(.*?)"\s*records\s*=\s*\[(.*?)\]\s*\}',
            re.DOTALL,
        )
        records = []
        for match in record_pattern.finditer(records_section):
            name = match.group(1).strip()
            type_ = match.group(2).strip()
            records_list = [
                record.strip().strip('"') for record in match.group(3).split(",")
            ]
            records.append({"name": name, "type": type_, "records": records_list})

        # Convert to JSON
        final_records = {"records": records}
        json_output = final_records
        print("Completed parsing data")
    else:
        print("No records section found.")

    return json_output


def process_single_input_data(user_input_str):
    # It process the data if single cname data is passed.
    """
    Example:
    {
      name    = "prometheus-use1-dev"
      type    = "CNAME"
      records = ["internal-k8s-monitori-monitori-7f7a470b92-39421355.us-east-2.elb.amazonaws.com"]
    }
    """
    user_input = user_input_str.strip("{}")
    user_input_dict = convert_string_to_dict(user_input)
    env = dns_details_env.replace('-','_')
    with open(f"input_data_parsed{env}.json", "w") as file:
        json.dump(user_input_dict, file)
    print("Parsed input data saved in input_data_parsed.json file")

    final_output_df = pd.DataFrame(
        columns=["Input Data", "Output Data", "Comments", "Processed Flag"]
    )
    final_output_df_temp = final_output_df.copy()
    final_output_df_temp["Input Data"] = [user_input_str]

    result_output_dict = format_user_input(user_input_dict)

    if result_output_dict:
        try:
            result_output_string = format_dict(result_output_dict)
            final_output_df_temp["Output Data"] = [result_output_string]
            final_output_df_temp["Processed Flag"] = [True]
            final_output_df_temp["Comments"] = [
                "The input data did meet the formatting requirements"
            ]
        except Exception as e:
            final_output_df_temp["Processed Flag"] = [False]
            final_output_df_temp["Comments"] = [
                "The input data did not meet the formatting requirements"
            ]

    else:
        final_output_df_temp["Processed Flag"] = [False]
        final_output_df_temp["Comments"] = [
            "The input data did not meet the formatting requirements"
        ]
        print(
            f"The input data did not meet the formatting requirements\n {user_input_str}"
        )

    with open(f"Final Formatted Output Data{env}.txt", "w") as file:
        file.write(result_output_string)

    final_output = pd.concat(
        [final_output_df, final_output_df_temp], axis=0, ignore_index=True
    )
    final_output_df_temp = final_output_df_temp.drop(final_output_df_temp.index)
    final_output.to_csv(rf"Final Formatted Output Data{env}.csv", index=False)


def process_multiple_input_data(user_input_str):
    
    # This function processes multiple input data like ,
    # It process the data if multiple cname data is passed.
    user_input_dict = parse_input_data(user_input_str)
    env = dns_details_env.replace('-','_')

    with open(f"input_data_parsed{env}.json", "w") as file:
        json.dump(user_input_str, file)
    print("Parsed input data saved in input_data_parsed.json file")

    if user_input_dict:
        final_output_df = pd.DataFrame(
            columns=["Input Data", "Output Data", "Comments", "Processed Flag"]
        )

        final_output_df_temp = final_output_df.copy()
        final_output_result = []
        for records in user_input_dict["records"]:
            final_output_df_temp["Input Data"] = [records]
            result_output_dict = format_user_input(records)

            if result_output_dict:
                try:
                    result_output_string = format_dict(result_output_dict)
                    final_output_df_temp["Output Data"] = [result_output_string]
                    final_output_df_temp["Processed Flag"] = [True]
                    final_output_df_temp["Comments"] = [
                        "The input data did meet the formatting requirements"
                    ]
                    final_output_result.append(result_output_string)

                except Exception as e:
                    final_output_df_temp["Processed Flag"] = [False]
                    final_output_df_temp["Comments"] = [
                        "The input data did not meet the formatting requirements"
                    ]
                    print("Error : {e}")
                
                

                final_output_df = pd.concat(
                                [final_output_df, final_output_df_temp], axis=0, ignore_index=True
                            )
                final_output_df_temp = final_output_df_temp.drop(final_output_df_temp.index)

        with open(f"Final Formatted Output Data{env}.txt", "w") as file:
            for data in final_output_result:
                file.write(data + '\n\n')

        final_output_df.to_csv(rf"Final Formatted Output Data{env}.csv", index=False)
        


if __name__ == "__main__":

    if single_input:
        print("Reading single input data from input file")
        with open(single_input_file_path, "r") as file:
            user_input_str = file.read()
        process_single_input_data(user_input_str)

    elif multipleInput:
        print("Reading multiple input data from input file")

        with open(multiple_Input_file_path, "r") as file:
            user_input_str = file.read()
        process_multiple_input_data(user_input_str)

    else:
        print("please hard code input data in code ")
        # Example
        user_input_str = """{
            name    = "prometheus-use1-dev"
            type    = "CNAME"
            records = ["internal-k8s-monitori-monitori-7f7a470b92-39421355.us-east-2.elb.amazonaws.com"]
            }"""
        process_single_input_data(user_input_str)
