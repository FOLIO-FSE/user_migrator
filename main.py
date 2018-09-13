import csv
import json
import argparse
from mappers.Aleph import Aleph
from mappers.Alabama import Alabama

parser = argparse.ArgumentParser()
parser.add_argument("source_path",
                    help="path of the source file. JSON...")
parser.add_argument("result_path",
                    help="path and name of the results file")
parser.add_argument("groups_map_path",
                    help="path of the group mapping file")
parser.add_argument("mapper",
                    help="which mapper to use")
args = parser.parse_args()

with open(args.groups_map_path, 'r') as groups_map_file:
    groups_map = list(csv.DictReader(groups_map_file))
    config = {"groupsmap": groups_map}
    mapper = Aleph(config)
    mapper = (Aleph(config) if args.mapper == 'aleph'
              else Alabama(config))
    import_struct = {"source_type": "test_hampat",
                     "deactivateMissingUsers": False,
                     "users": [],
                     "updateOnlyPresentFields": False,
                     "totalRecords": 0}
with open(args.result_path, 'w+') as results_file:
    with open(args.source_path, 'r') as source_file:
        users = mapper.get_users(source_file)
        for user in users:
            import_struct["users"].append(mapper.do_map(user))
        import_struct["totalRecords"] = len(import_struct["users"])
    results_file.write(json.dumps(import_struct, indent=4))
