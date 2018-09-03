import csv
import json
import argparse
from mappers.Aleph import Aleph

parser = argparse.ArgumentParser()
parser.add_argument("source_path",
                    help="path of the source file. JSON...")
parser.add_argument("result_path",
                    help="path and name of the results file")
parser.add_argument("groups_map_path",
                    help="path of the group mapping file")
args = parser.parse_args()

with open(args.groups_map_path, 'r') as groups_map_file:
    groups_map = list(csv.DictReader(groups_map_file))
    config = {"groupsmap": groups_map}
    mapper = Aleph(config)
    import_struct = {"source_type": "test_hampat",
                     "deactivateMissingUsers": False,
                     "users": [],
                     "updateOnlyPresentFields": False,
                     "totalRecords": 0}
with open(args.result_path, 'w+') as results_file:
    with open(args.source_path, 'r') as source_file:
        users = json.load(source_file)["p-file-20"]["patron-record"]
        for user in users:
            import_struct["users"].append(mapper.do_map(user))
        import_struct["totalRecords"] = len(import_struct["users"])
    results_file.write(json.dumps(import_struct, indent=4))
