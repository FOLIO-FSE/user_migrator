import argparse
import csv
import itertools
import json
import os
import uuid
import random

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_file", help="path of the source file. JSON...")
    parser.add_argument("result_file", help="path and name of the results file")
    args = parser.parse_args()
    i = 0
    with open(args.source_file, "r") as groups_map_file:
        users = csv.DictReader(groups_map_file, delimiter="\t")
        with open(args.result_file, "w+") as id_map_file:
            for user in users:
                i += 1
                new_user = populate_user(user, i)
                print(f"{new_user['id']}\t{json.dumps(new_user)}", file=id_map_file)
                if i % 100 == 0:
                    print(f"{i}")


def populate_user(m_user, i):
    user = {}
    user["username"] = f"username:{i}"
    user["id"] = str(uuid.uuid4())
    user["externalSystemId"] = f"externalsystemid:{i}"
    user["barcode"] = f"00000{i}"
    user["active"] = True
    user["patronGroup"] = get_group()
    user["personal"] = {}
    user["personal"]["lastName"] = m_user["personal.lastName"]
    user["personal"]["firstName"] = m_user["firstName"]
    user["personal"]["middleName"] = m_user["personal.middleName"]
    user["personal"]["email"] = m_user["personal.email"]
    user["personal"]["phone"] = m_user["personal.phone"]
    user["personal"]["dateOfBirth"] = m_user["personal.dateOfBirth"]
    user["personal"]["addresses"] = [{}]
    user["personal"]["addresses"][0]["id"] = str(uuid.uuid4())
    user["personal"]["addresses"][0]["countryId"] = m_user[
        "personal.addresses.countryId"
    ]
    user["personal"]["addresses"][0]["addressLine1"] = m_user[
        "personal.addresses.addressLine1"
    ]
    user["personal"]["addresses"][0]["city"] = m_user["personal.addresses.city"]
    user["personal"]["addresses"][0]["region"] = m_user["personal.addresses.region"]
    user["personal"]["addresses"][0]["postalCode"] = m_user[
        "personal.addresses.postalCode"
    ]
    user["personal"]["addresses"][0][
        "addressTypeId"
    ] = "ae749f82-a4ef-47ca-b29c-0a5ad7bbff03"
    user["personal"]["addresses"][0]["primaryAddress"] = True
    user["personal"]["preferredContactTypeId"] = "001"
    return user


def get_group():
    group_ids = [
        "06f2d60e-0b07-49ca-b8c7-e1d49808e0b7",
        "8bbb4e68-0077-4fe1-ad4a-3ab3cfec0766",
        "b140cdcb-5159-4fca-aafc-cc5e9ddfa125",
        "10ed499c-19c2-4bb2-bff9-15bc559fe36a",
        "b17b6b34-6517-4dbe-8245-3e47a7a73f91",
        "0fa228a0-b4f3-4a58-b767-04bbf630c2c5",
        "9633b57f-44c6-44b6-890f-b7fb599236fd",
        "7da4ba23-cfc5-4aec-bdb2-ee6720b0b76d",
        "470a1e14-9854-430f-a490-e4f4e56c2a67",
        "b30466f5-d8fc-407a-9000-8f3576e4e88a",
        "3474f19b-1a65-4314-9e22-6ff808164262",
        "46dd39b5-a17c-421b-9e88-cf24e297ba4d",
        "c64b701a-8268-4162-9b36-3f704b93717d",
        "dea545b4-5d0f-43d2-b2fe-a43a39cb345d",
        "32274b17-90d6-4185-aa95-ce1c981a87ec",
        "2d1d0e03-8cca-4f35-8143-f6ca2abbea98",
        "294db32c-0675-4dd5-8c5f-e3974c4ab6f2",
        "648ec9f2-c292-4e74-932b-9e5cf059d4d6",
        "147c1f20-6daf-4561-ab13-f652fbe16d38",
        "54c89e59-0781-4a1a-b5c7-8221b5d97a16",
        "1302457c-ddc3-4205-ad19-5bda613d0914",
        "bd0203da-a5c4-4a7e-8140-765fe9d851ff",
        "24bc1e53-93f3-4c7b-930d-e87dd46a7cec",
        "2a77b5ea-132d-47ba-97ee-c2e6d6afdedf",
        "9d83bbff-bd23-45e4-9192-d987ae73fe63",
        "24c42fec-8a8a-4696-9a57-d0533c5470d1",
        "e7d47de9-5b49-4859-b091-e32a74d11313",
        "a7a08fce-a678-405f-9eef-058206e89abe",
        "8fb6e9fa-045c-40b8-a5a4-d42f42d3afa2",
        "28bf3a28-b509-463c-b5e1-da787bc017fb",
    ]
    return random.choice(group_ids)


if __name__ == "__main__":
    main()
