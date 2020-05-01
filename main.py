import argparse
import csv
import itertools
import json
import os

import requests
import usaddress
import pathlib
from jsonschema import ValidationError, validate
from mappers.Alabama import Alabama
from mappers.AlabamaBanner import AlabamaBanner
from mappers.Chalmers import Chalmers
from mappers.FiveColleges import FiveColleges
from mappers.MsuMigration import MsuMigration


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_path", help="path of the source file. JSON...")
    parser.add_argument("result_path", help="path and name of the results file")
    parser.add_argument("groups_map_path", help="path of the group mapping file")
    parser.add_argument("mapper", help="which mapper to use")
    parser.add_argument("source_name", help="source name")
    args = parser.parse_args()
    user_schema = get_user_schema()
    id_map = {}
    barcode_map = {}
    username_map = {}
    external_user_id_map = {}
    user_id_map_path = os.path.join(args.result_path, "patron_id_map.json")
    blocks_path = os.path.join(args.result_path, "patron_blocks.json")
    notes_path = os.path.join(args.result_path, "patron_notes.json")
    groups_path = args.groups_map_path
    print("getting user group mappings from {}".format(groups_path))
    print("saving results to {}".format(args.result_path))
    with open(groups_path, "r") as groups_map_file:
        groups_map = list(csv.DictReader(groups_map_file, delimiter="\t"))
    print("Number of groups to map: {}".format(len(groups_map)))
    config = {"groupsmap": groups_map}
    mapper = get_mapper(args.mapper, config)
    folio_users_per_group = {}
    sierra_users_per_group = {}
    import_struct = {
        "source_type": args.source_name,
        "deactivateMissingUsers": False,
        "users": [],
        "updateOnlyPresentFields": False,
        "totalRecords": 0,
    }
    with open(args.source_path, "r") as source_file, open(
        notes_path, "w+"
    ) as notes_file, open(blocks_path, "w+") as blocks_file:
        file_name = os.path.basename(source_file.name).replace(".json", "")
        total_users = 0
        i = 0
        failed_users = 0
        last_counter = dict()
        users_json = mapper.get_users(source_file)
        chunks = make_chunks(users_json, 100)
        for chunk in chunks:
            i += 1
            import_struct["users"] = []
            for user_json in chunk:
                old_id = None
                total_users += 1
                try:
                    user, old_id, notes, block = mapper.do_map(user_json[0])
                    patron_group = map_user_group(groups_map, user)
                    validate(user, user_schema)
                    if patron_group not in folio_users_per_group:
                        folio_users_per_group[patron_group] = 1
                    else:
                        folio_users_per_group[patron_group] += 1
                    if old_id not in id_map:
                        id_map[old_id] = {
                            "id": user["id"],
                            "patron_type_id": patron_group,
                        }
                    else:
                        raise ValueError("Duplicate user id for {}".format(old_id))
                    # patron group is mapped and set
                    dupe_id_check(barcode_map, old_id, user["barcode"], "barcode")
                    dupe_id_check(
                        external_user_id_map,
                        old_id,
                        user["externalSystemId"],
                        "externalSystemId",
                    )
                    dupe_id_check(username_map, old_id, user["username"], "username")
                    if patron_group != "":
                        user["patronGroup"] = patron_group
                        import_struct["users"].append(user)
                        if block:
                            print(json.dumps(block), file=blocks_file)
                        for note in notes:
                            print(json.dumps(note), file=notes_file)
                    last_counter = user_json[1]
                    import_struct["totalRecords"] = len(import_struct["users"])
                except ValueError as value_error:
                    if old_id and old_id in id_map:
                        del id_map[old_id]
                    failed_users += 1
                    print(str(value_error))
                except usaddress.RepeatedLabelError as rle:
                    if old_id and old_id in id_map:
                        del id_map[old_id]
                    failed_users += 1
                    print("Failed parsing address for user")
                    print(user_json)
                    print(str(rle))
            path = "{}/{}_{}_{}.json".format(
                args.result_path, args.source_name, file_name, str(i)
            )
            with open(path, "w+") as results_file:
                results_file.write(json.dumps(import_struct, indent=4))
        with open(user_id_map_path, "w+") as id_map_file:
            id_map_file.write(json.dumps(id_map, indent=4))
        print("III Users per group")
        print(json.dumps(sierra_users_per_group, sort_keys=True, indent=4))
        print("FOLIO Users per group")
        print(json.dumps(folio_users_per_group, sort_keys=True, indent=4))
        print(
            "Number of failed users:\t{} out of {} processed users in total after filtering.".format(
                failed_users, total_users
            )
        )
        print(json.dumps(last_counter, sort_keys=True, indent=4))


def get_mapper(mapperName, config):
    return {
        "alabama": Alabama,
        "alabama_banner": AlabamaBanner,
        "five_colleges": FiveColleges,
        "chalmers": Chalmers,
        "msu": MsuMigration,
    }[mapperName](config)


def get_user_schema():
    schema_location = "https://raw.githubusercontent.com/folio-org/mod-user-import/master/ramls/schemas/userdataimport.json"
    req = requests.get(schema_location)
    return json.loads(req.text)


def make_chunks(my_list, size):
    iterator = iter(my_list)
    for first in iterator:
        yield itertools.chain([first], itertools.islice(iterator, size - 1))


def map_user_group(groups_map, user):

    folio_group = next(
        (g["Folio Code"] for g in groups_map if g["ILS code"] == user["patronGroup"]),
        "unmapped",
    )
    return folio_group


def dupe_id_check(id_map, user_id, id_to_add, type_string):
    if id_to_add not in id_map:
        id_map[id_to_add] = user_id
    else:
        if id_to_add:
            raise ValueError(
                "Duplicate {} ({}) for {}".format(type_string, id_to_add, user_id)
            )


if __name__ == "__main__":
    main()
