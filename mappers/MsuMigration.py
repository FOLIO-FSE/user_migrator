import csv
import io
import json
import re
import uuid
import traceback
from datetime import datetime as dt

import requests


class MsuMigration:
    # TODO:Bring over number of loans
    # (fixed fields 50) and sum them up.

    def __init__(self, config):
        # TODO: Move country codes to central implementation
        country_codes_url = (
            "https://raw.githubusercontent.com/"
            "datasets/country-codes/master/data/"
            "country-codes.csv"
        )
        req = requests.get(country_codes_url)
        self.country_data = list(csv.DictReader(io.StringIO(req.text)))
        self.default_email = "ttolstoy@ebsco.com"
        self.counters = {}
        self.sierra_users_per_group = {}
        self.migration_report = {}
        self.counters["pmessage_counts"] = {}
        self.counters["blockinfo"] = {}

    def do_map(self, user):
        add_stats(
            self.counters,
            "Total number of checkouts for all users",
            self.get_current_checked_out(user),
        )
        bc = self.get_barcode_values(user)
        add_stats(self.sierra_users_per_group, str(user["patronType"]))
        new_user = {
            "username": self.get_username(user),
            "id": str(uuid.uuid4()),
            "externalSystemId": bc["externalSystemId"],
            "barcode": bc["barcode"],
            "patronGroup": str(user["patronType"]),
            "active": self.get_active(user),
            "personal": {
                "lastName": self.get_names(user)[0],
                "firstName": self.get_names(user)[1],
                "preferredContactTypeId": "email",
                "email": self.get_email(user)
                #  "enrollmentDate":
            },
            "expirationDate": user["expirationDate"],
            "type": "object",
        }
        add_stats(
            self.counters,
            "Total number of checkouts for successfully migrated users",
            self.get_current_checked_out(user),
        )
        notes = self.create_notes(user, new_user)
        block = self.create_blocks(user, new_user)
        new_user["personal"]["email"] = "FOLIOcirc@library.missouristate.edu"
        return new_user, user["id"], notes, block

    def add_to_migration_report(self, header, messageString):
        # TODO: Move to interface or parent class
        if header not in self.migration_report:
            self.migration_report[header] = list()
        self.migration_report[header].append(messageString)

    def get_users(self, source_file):
        print("")
        for line in source_file:
            add_stats(self.counters, "Total users in file")
            if self.counters["Total users in file"] % 100 == 0:
                print(
                    f'{self.counters["Total users in file"]} users processed', end="\r"
                )
            try:
                user_json = json.loads(line)
                # Filter out deleted users
                if user_json["deleted"] is True:
                    add_stats(self.counters, "Deleted users in file")
                # Filter out suppressed patrons
                elif user_json["suppressed"] is True:
                    add_stats(self.counters, "Suppressed users in file")
                else:
                    add_stats(
                        self.counters, f'Blockinfo: {user_json["blockInfo"]["code"]}'
                    )
                    if user_json["pMessage"].strip() != "":
                        add_stats(
                            self.counters, "Number of users with pMessages in Total"
                        )
                        add_stats(
                            self.counters,
                            f'Number of users with pMessages {user_json["pMessage"]}',
                        )
                    temp_date = dt.now()
                    temp_date_str = temp_date.strftime("%Y-%m-%d")
                    exp_date = dt.strptime(
                        user_json.get("expirationDate", temp_date_str), "%Y-%m-%d"
                    )
                    if exp_date < temp_date:
                        if (
                            self.get_current_checked_out(user_json) > 0
                            or float(user_json["fixedFields"]["96"]["value"]) > 0
                        ):
                            add_stats(
                                self.counters, "Expired users with loans or money owned"
                            )
                        user_json["expirationDate"] = temp_date_str
                        add_stats(
                            self.counters,
                            "Expired users, seting today as expiration date",
                        )
                    yield [user_json, self.counters]
            except Exception as ee:
                print(ee)
                traceback.print_exc()
                print(line)

    def create_blocks(self, user, folio_user):
        blockinfo = user.get("blockInfo", {}).get("code", "")
        codes = {"a": "check address", "m": "mobius block", "u": "unpaid bill"}
        if blockinfo in ["m", "u", "a"]:
            add_stats(self.counters, "Created blocks")
            return {
                "borrowing": True,
                "renewals": True,
                "requests": True,
                "desc": codes.get(blockinfo, ""),
                "type": "Manual",
                "userId": folio_user["id"],
                "id": str(uuid.uuid4()),
            }

    def create_notes(self, user, folio_user):
        add_stats(self.counters, "Created notes - Total")
        # migrated values note
        yield {
            "domain": "users",
            "typeId": "d4c8fc9e-7306-4c4c-90ec-c8a805acf1d0",
            "content": (
                f'<p>.p-number: {user["id"]}</p> '
                f'<p>current checkouts: {int(user["fixedFields"]["50"]["value"])}</p> '
                f'<p>total checkouts: {int(user["fixedFields"]["48"]["value"])}</p> '
                f'<p>total renewals: {int(user["fixedFields"]["49"]["value"])}</p> '
                f'<p>ammount owned: {float(user["fixedFields"]["96"]["value"])}</p> '
                f'<p>p message: {user["fixedFields"]["54"]["value"]}</p> '
                f'<p>p codes: {json.dumps(user["patronCodes"])}</p> '
                f'<p>patron type: {user["patronType"]}</p> '
            ),
            "title": "Migrated Values",
            "links": [{"type": "user", "id": folio_user["id"]}],
            "id": str(uuid.uuid4()),
        }
        # x notes
        for x in get_varfields_no_subfield(user, "x"):
            add_stats(self.counters, "Created notes - Total")
            add_stats(self.counters, "Created notes - x")
            yield {
                "domain": "users",
                "typeId": "b6e8babb-92db-43c5-8b2b-aec170702926",
                "content": x,
                "title": "Patron Note",
                "links": [{"type": "user", "id": folio_user["id"]}],
                "id": str(uuid.uuid4()),
            }

    def get_username(self, user):
        uname = next(get_varfields_no_subfield(user, "u"), "")
        if not uname:
            raise ValueError(f"No username present for user {user['id']}")
        return uname

    def get_email(self, user):
        if "emails" not in user:
            add_stats(self.counters, "Email - no emails attribute")
            self.add_to_migration_report(
                "User Email Issues", f'No emails attribute for {user["id"]}'
            )
            return self.default_email
        elif len(user["emails"]) > 1:
            add_stats(self.counters, "more_than_one_emails")
            msu_email = next(
                (e for e in user["emails"] if "missouristate.edu" in e), ""
            )
            if msu_email:
                add_stats(self.counters, "more_than_one_emails - missouristate.edu")
                return msu_email
            add_stats(self.counters, f"{user['id']}")
            return user["emails"][0]
        elif not user["emails"]:
            add_stats(self.counters, "Email - empty emails attribute")
            self.add_to_migration_report(
                "User Email Issues", f'Zero emails for {user["id"]}'
            )
            return self.default_email
        else:
            eml = user["emails"][0]
            reg = r"[^@]+@[^@]+\.[^@]+"
            if not re.match(reg, eml):
                add_stats(self.counters, "Email - Likely invalid")
                self.add_to_migration_report(
                    "User Email Issues",
                    "email likely invalid {} for user {}".format(eml, user["id"]),
                )
                return self.default_email
            else:
                return eml

    def get_barcode_values(self, user):
        barcodes = user.get("barcodes", [])
        folio_barcode = ""
        m_number = ""
        other = False
        if not barcodes:
            raise ValueError(f'No barcodes for  {user["id"]}')
        for barcode in (bc.strip() for bc in barcodes):
            if barcode.startswith("M"):
                m_number = barcode
            elif len(barcode) == 16 or str(barcode).startswith("22356"):
                folio_barcode = barcode
            else:
                other = True
                self.add_to_migration_report(
                    "Barcode issues", f"other barcode {barcode} for user {user['id']}"
                )
        if other and not folio_barcode:
            self.add_to_migration_report(
                "Barcode issues", f"Other barcode and no barcode for user {user['id']}"
            )
        if other and not m_number:
            self.add_to_migration_report(
                "Barcode issues", f"Other barcode and no m_number for user {user['id']}"
            )
        return {
            "externalSystemId": (m_number),
            "barcode": folio_barcode if folio_barcode else m_number,
        }

    def get_current_checked_out(self, user):
        return int(user["fixedFields"]["50"]["value"])

    def get_ext_uid(self, user):
        if "barcodes" in user:
            if len(user["barcodes"]) > 1:
                for b in user["barcodes"]:
                    if b.startswith("M"):
                        add_stats(self.counters, "ext_id_barcode")
                        return f"BARCODE:{b}"
        else:
            ids = user.get("uniqueIds", [])
            if len(ids) == 0:
                print(f"No uniqueIds for {user['id']}")
            elif len(ids) == 1:
                add_stats(self.counters, "ext_id_unique_id")
                f"UNIQUEID:{ids[0]}"
            elif len(ids) > 1:
                print(f"more than one uniqueIds for {user['id']}")
                add_stats(self.counters, "ext_id_unique_id")
                return f"UNIQUEID:{ids[0]}"
        return ""

    def get_active(self, user):
        return True

    def get_names(self, user):
        if "names" not in user:
            raise ValueError(f"no names attrib for {user['id']}")
        if len(user["names"]) > 1:
            raise ValueError(f"Too many names for {user['id']}")
        elif not user["names"]:
            raise ValueError(f"Zero names for {user['id']}")
        elif ", " not in user["names"][0]:
            if user["patronType"] not in [110, 120, 130, 140, 150, 200, 201]:
                raise ValueError(f"No comma in name for {user['id']}")
            return [user["names"][0], ""]
        else:
            return user["names"][0].split(", ")

    def get_expiration_date(self, user):
        return user["expirationDate"]


def gen_dict_extract(key, var):
    if hasattr(var, "iteritems"):
        for k, v in var.iteritems():
            if k == key:
                yield v
            if isinstance(v, dict):
                for result in gen_dict_extract(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in gen_dict_extract(key, d):
                        yield result


def find(element, json):
    keys = element.split(".")
    rv = json
    for key in keys:
        rv = rv[key]
        return rv


def add_stats(stats, a, value=1):
    if a not in stats:
        stats[a] = value
    else:
        stats[a] += value


def validate(
    stats_map, folio_object,
):
    for key, value in folio_object.items():
        if isinstance(value, str) and any(value):
            add_stats(stats_map, key)
        if isinstance(value, list) and any(value):
            add_stats(stats_map, key)


def get_varfields_no_subfield(sierra_item, field_tag):
    try:
        return (
            vf.get("content", "")
            for vf in sierra_item["varFields"]
            if field_tag in vf["fieldTag"]
        )
    except Exception as ee:
        print(ee)
        print(sierra_item)
        raise ee
