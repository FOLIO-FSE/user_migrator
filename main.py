import csv
import json
import argparse
from mappers.Aleph import Aleph
from mappers.Alabama import Alabama
from mappers.AlabamaBanner import AlabamaBanner
from mappers.Chalmers import Chalmers


def get_mapper(mapperName, config):
    return {
        'alabama': Alabama(config),
        'alabama_banner': AlabamaBanner(config),
        'aleph': Aleph(config),
        'chalmers': Chalmers(config)
    }[mapperName]


def chunks(myList, n):
    for i in range(0, len(myList), n):
        yield myList[i:i+n]


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
    mapper = get_mapper(args.mapper, config)
    import_struct = {"source_type": "test_hampat",
                     "deactivateMissingUsers": False,
                     "users": [],
                     "updateOnlyPresentFields": False,
                     "totalRecords": 0}
    with open(args.source_path, 'r') as source_file:
        i = 0
        users = mapper.get_users(source_file)
        cs = chunks(users, 100)
        for c in cs:
            i += 1
            import_struct["users"] = []
            for user in c:
                import_struct["users"].append(mapper.do_map(user))
                import_struct["totalRecords"] = len(import_struct["users"])
            path = args.result_path + str(i) + '.json'
            with open(path, 'w+') as results_file:
                results_file.write(json.dumps(import_struct, indent=4))
