import argparse
import csv
import itertools
import json
import os

import usaddress
from mappers.Alabama import Alabama
from mappers.AlabamaBanner import AlabamaBanner
from mappers.Chalmers import Chalmers
from mappers.FiveColleges import FiveColleges


def get_mapper(mapperName, config):
    return {
        'alabama': Alabama,
        'alabama_banner': AlabamaBanner,
        'five_colleges': FiveColleges,
        'chalmers': Chalmers
    }[mapperName](config)


def make_chunks(my_list, size):
    iterator = iter(my_list)
    for first in iterator:
        yield itertools.chain([first], itertools.islice(iterator, size - 1))


def map_user_group(groups_map, user):
    folio_group = next((g['Folio Code'] for g
                        in groups_map
                        if g['ILS code'] == user['patronGroup']), 'unmapped')
    if folio_group == 'unmapped':
        raise ValueError("source patron group error: {} for {}"
                         .format(user['patronGroup'], user['id']))
    else:
        return folio_group


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_path",
                        help="path of the source file. JSON...")
    parser.add_argument("result_path",
                        help="path and name of the results file")
    parser.add_argument("groups_map_path",
                        help="path of the group mapping file")
    parser.add_argument("mapper",
                        help="which mapper to use")
    parser.add_argument("source_name",
                        help="source name")
    parser.add_argument("id_map_path",
                        help="Where to save user id mappings file")
    args = parser.parse_args()
    id_map = {}
    groups_path = args.groups_map_path + '/user_groups.tsv'
    with open(groups_path, 'r') as groups_map_file:
        groups_map = list(csv.DictReader(groups_map_file, delimiter='\t'))
        config = {"groupsmap": groups_map}
        mapper = get_mapper(args.mapper, config)
        import_struct = {"source_type": args.source_name,
                         "deactivateMissingUsers": False,
                         "users": [],
                         "updateOnlyPresentFields": False,
                         "totalRecords": 0}
        with open(args.source_path, 'r') as source_file:
            file_name = os.path.basename(source_file.name).replace('.json', '')
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
                    try:
                        total_users += 1
                        user, old_id = mapper.do_map(user_json[0])
                        patron_group = map_user_group(groups_map, user)
                        if old_id not in id_map:
                            map_struct = {
                                'id': user['id'],
                                'patron_type_id': patron_group
                            }
                            id_map[old_id] = map_struct
                        else:
                            raise ValueError("Duplicate user id for {}"
                                             .format(old_id))
                        # patron group is mapped and set
                        if patron_group != '':
                            user['patronGroup'] = patron_group
                            import_struct["users"].append(user)
                        last_counter = user_json[1]
                        import_struct["totalRecords"] = len(import_struct["users"])
                    except ValueError as value_error:
                        failed_users += 1
                        print(str(value_error))
                    except usaddress.RepeatedLabelError as rle:
                        failed_users += 1
                        print("Failed parsing address for user")
                        print(user_json)
                        print(str(rle))
                path = "{}/{}_{}_{}.json".format(args.result_path,
                                                 args.source_name,
                                                 file_name,
                                                 str(i))
                with open(path, 'w+') as results_file:
                    results_file.write(json.dumps(import_struct, indent=4))
            with open(args.id_map_path, 'w+') as id_map_file:
                id_map_file.write(json.dumps(id_map, indent=4))
            print("Number of failed users:\t{} out of {} in total"
                  .format(failed_users, total_users))
            print(last_counter)


if __name__ == '__main__':
    main()
