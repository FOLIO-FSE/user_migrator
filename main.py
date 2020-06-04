import argparse
import csv
import itertools
import json
import os
import copy
import requests
import usaddress
import pathlib
from jsonschema import ValidationError, validate
from mappers.Alabama import Alabama
from mappers.AlabamaBanner import AlabamaBanner
from mappers.Chalmers import Chalmers
from mappers.FiveColleges import FiveColleges
from mappers.MsuMigration import MsuMigration
from folioclient.FolioClient import FolioClient


class Worker:
    """Class that is responsible for the acutal work"""

    def __init__(
        self, mapper, results_path, blocks_file, notes_file, chunks, groups_map
    ):
        self.groups_map = groups_map
        self.results_path = results_path
        self.blocks_file = blocks_file
        self.notes_file = notes_file
        self.stats = {}
        self.mapper = mapper
        self.migration_report = {}
        self.user_schema = get_user_schema()
        self.id_map = {}
        self.chunks = chunks
        self.folio_users_per_group = {}
        self.sierra_users_per_group = {}
        self.barcode_map = {}
        self.username_map = {}
        self.external_user_id_map = {}
        self.import_struct = {
            "source_type": "",
            "deactivateMissingUsers": False,
            "users": [],
            "updateOnlyPresentFields": False,
            "totalRecords": 0,
        }

    def work(self):
        print("Starting....")
        for chunk in self.chunks:
            add_stats(self.stats, "Number of batches")
            self.import_struct["users"] = []
            for user_json in chunk:
                legacy_sytem_id = None
                add_stats(self.stats, "Total Legacy Users processed")
                try:
                    user, legacy_sytem_id, notes, block = self.mapper.do_map(
                        user_json[0]
                    )
                    patron_group = self.map_user_group(user)
                    # validate(user, self.user_schema)
                    add_stats(self.folio_users_per_group, patron_group)
                    no_dupes = self.check_dupes(user, legacy_sytem_id, patron_group)

                    if no_dupes and patron_group != "":
                        user["patronGroup"] = patron_group
                        self.add_to_id_map(user, legacy_sytem_id)
                        self.import_struct["users"].append(user)
                        if block:
                            print(json.dumps(block), file=self.blocks_file)
                        for note in notes:
                            print(json.dumps(note), file=self.notes_file)
                        add_stats(self.stats, "Created FOLIO Users")
                    self.import_struct["totalRecords"] = len(
                        self.import_struct["users"]
                    )

                except ValueError as value_error:
                    if legacy_sytem_id and legacy_sytem_id in id_map:
                        del id_map[legacy_sytem_id]
                    add_stats(self.stats, "Total Users that failed")
                    add_stats(self.stats, "Failed Users - Value errors")
                    self.add_to_migration_report(
                        "Failed Users - Value errors", str(value_error)
                    )
                except usaddress.RepeatedLabelError as rle:
                    if legacy_sytem_id and legacy_sytem_id in id_map:
                        del id_map[legacy_sytem_id]
                    add_stats(self.stats, "Failed Users - Repeated Label error")
                    add_stats(self.stats, "Total Users that failed")
                    self.add_to_migration_report(
                        "Failed Users - Value errors",
                        f"Failed parsing address {str(rle)} for user {json.dumps(user_json)}",
                    )

            path = "{}/{}_{}.json".format(
                self.results_path,
                "users",
                str(add_stats(self.stats, "Number of batches")),
            )
            with open(path, "w+") as results_file:
                results_file.write(json.dumps(self.import_struct, indent=4))

    def add_to_id_map(self, user, legacy_sytem_id):
        if legacy_sytem_id not in self.id_map:
            self.id_map[legacy_sytem_id] = {
                "id": user["id"],
                "patron_type_id": user["patronGroup"],
            }
        else:
            raise Exception("Duplicate Legacy user id")

    def check_dupes(self, user, legacy_sytem_id, patron_group):
        no_dupes = True
        if legacy_sytem_id in self.id_map:
            no_dupes = False
            add_stats(self.stats, "Duplicate values - Legacy Ids")
        try:
            dupe_id_check(self.barcode_map, legacy_sytem_id, user, "barcode")
        except ValueError as ve:
            no_dupes = False
            add_stats(self.stats, "Duplicate values - Barcode")
            self.add_to_migration_report("Duplicate Barcodes - Must correct", str(ve))
        try:
            dupe_id_check(
                self.external_user_id_map, legacy_sytem_id, user, "externalSystemId",
            )
        except ValueError as ve:
            no_dupes = False
            add_stats(self.stats, "Duplicate values - External System Id")
            self.add_to_migration_report(
                "Duplicate externalSystemId - Must correct", str(ve)
            )
        try:
            dupe_id_check(self.username_map, legacy_sytem_id, user, "username")
        except ValueError as ve:
            no_dupes = False
            add_stats(self.stats, "Duplicate values - Username")
            self.add_to_migration_report("Duplicate username - Must correct", str(ve))
        return no_dupes

    def add_to_migration_report(self, header, messageString):
        # TODO: Move to interface or parent class
        if header not in self.migration_report:
            self.migration_report[header] = list()
        self.migration_report[header].append(messageString)

    def wrap_up(self):
        print("Done. Wrapping up...")
        print("# User Transformation Results")
        print("## Statistics")
        self.stats = {**self.stats, **self.mapper.counters}
        print_dict_to_md_table(self.stats, "Measure", "Count")

        print("## Sierra/III Users per group")
        print_dict_to_md_table(
            self.sierra_users_per_group, "Sierra User group", "Count"
        )

        print("## FOLIO Users per group")
        print_dict_to_md_table(self.folio_users_per_group, "FOLIO User Group", "Count")
        self.write_migration_report()
        self.write_migration_report(self.mapper.migration_report)

    def add_to_migration_report(self, header, messageString):
        # TODO: Move to interface or parent class
        if header not in self.migration_report:
            self.migration_report[header] = list()
        self.migration_report[header].append(messageString)

    def write_migration_report(self, other_report=None):
        if other_report:
            for a in other_report:
                print(f"## {a}")
                for b in sorted(other_report[a]):
                    print(f"{b}\\")
        else:
            for a in self.migration_report:
                print(f"## {a}")
                for b in sorted(self.migration_report[a]):
                    print(f"{b}\\")

    def map_user_group(self, user):
        folio_group = next(
            (
                g["Folio Code"]
                for g in self.groups_map
                if g["ILS code"] == user["patronGroup"]
            ),
            "unmapped",
        )
        return folio_group


def parse_args():
    """Parse CLI Arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("source_path", help="path of the source file. JSON...")
    parser.add_argument("results_path", help="path and name of the results file")
    parser.add_argument("groups_map_path", help="path of the group mapping file")
    parser.add_argument("mapper", help="which mapper to use")
    parser.add_argument("source_name", help="source name")
    args = parser.parse_args()
    return args


def get_mapper(mapperName, config):
    return {
        "alabama": Alabama,
        "alabama_banner": AlabamaBanner,
        "five_colleges": FiveColleges,
        "chalmers": Chalmers,
        "msu": MsuMigration,
    }[mapperName](config)


def get_user_schema():
    schema_location = (
        "https://raw.githubusercontent.com/folio-org/mod-user-import"
        "/master/ramls/schemas/userdataimport.json"
    )
    req = requests.get(schema_location)
    return json.loads(req.text)


def dupe_id_check(id_map, legacy_id, user, type_string):
    if not user[type_string]:
        raise ValueError(f"EMPTY {type_string} ({user[type_string]}) for {legacy_id}")
    elif user[type_string] not in id_map:
        id_map[user["id"]] = legacy_id
    else:
        raise ValueError(
            "Duplicate {} ({}) for {}".format(type_string, user[type_string], legacy_id)
        )


def make_chunks(my_list, size):
    iterator = iter(my_list)
    for first in iterator:
        yield itertools.chain([first], itertools.islice(iterator, size - 1))


def print_dict_to_md_table(my_dict, h1, h2):
    # TODO: Move to interface or parent class
    d_sorted = {k: my_dict[k] for k in sorted(my_dict)}
    print(f"{h1} | {h2}")
    print("--- | ---:")
    for k, v in d_sorted.items():
        print(f"{k} | {v}")


def add_stats(stats, a):
    if a not in stats:
        stats[a] = 1
    else:
        stats[a] += 1


def main():
    args = parse_args()
    print("\tresults will be saved at:\t", args.results_path)

    user_id_map_path = os.path.join(args.results_path, "patron_id_map.json")
    blocks_path = os.path.join(args.results_path, "patron_blocks.json")
    notes_path = os.path.join(args.results_path, "patron_notes.json")
    print(f"getting user group mappings from {args.groups_map_path}")
    print(f"saving results to {args.results_path}")

    with open(args.source_path, "r") as source_file, open(
        args.groups_map_path, "r"
    ) as groups_map_file, open(notes_path, "w+") as notes_file, open(
        blocks_path, "w+"
    ) as blocks_file:
        groups_map = list(csv.DictReader(groups_map_file, delimiter="\t"))
        print(f"Number of groups to map: {len(groups_map)}")
        config = {}
        mapper = get_mapper(args.mapper, config)

        users_json = mapper.get_users(source_file)
        chunks = make_chunks(users_json, 500)

        # Initiate Worker
        worker = Worker(
            mapper, args.results_path, blocks_file, notes_file, chunks, groups_map
        )
        worker.work()

        with open(user_id_map_path, "w+") as id_map_file:
            id_map_file.write(json.dumps(worker.id_map, indent=4))
        worker.wrap_up()


if __name__ == "__main__":
    main()
