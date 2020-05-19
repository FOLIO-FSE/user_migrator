import csv
import io
import json
import re
import uuid
from datetime import datetime as dt

import requests


class MsuMigration:
    # TODO:Bring over number of loans
    # (fixed fields 50) and sum them up.

    def __init__(self, config):
        self.groupsmap = config["groupsmap"]
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
        self.counters["pmessage_counts"] = {}
        self.counters["blockinfo"] = {}

    def do_map(self, user):
        add_stats(self.counters, "tot_checkedout", self.get_current_checked_out(user))
        bc = self.get_barcode_values(user)
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
            self.counters, "successful_checkedout", self.get_current_checked_out(user)
        )
        notes = self.create_notes(user, new_user)
        block = self.create_blocks(user, new_user)
        user["personal"]["email"] = "FOLIOcirc@library.missouristate.edu"
        return new_user, user["id"], notes, block

    def get_users(self, source_file):
        for line in source_file:
            add_stats(self.counters, "total2")
            user_json = json.loads(line)
            try:
                # if user_json['id'] in ['1021461','1023445', '1132876']:
                #    print(user_json)
                # Filter out deleted users
                if user_json["deleted"] is True:
                    add_stats(self.counters, "deleted")
                # Filter out suppressed patrons
                elif user_json["suppressed"] is True:
                    add_stats(self.counters, "suppressed")
                # Filter out blocked patrons
                # elif user_json['blockInfo']['code'] != '-':
                #     add_stats(self.counters, 'blocked')
                else:
                    add_stats(
                        self.counters["blockinfo"], user_json["blockInfo"]["code"]
                    )
                    if user_json["pMessage"].strip() != "":
                        add_stats(self.counters, "pMessage_count")
                        add_stats(
                            self.counters["pmessage_counts"], user_json["pMessage"]
                        )
                    exp_date = dt.strptime(user_json["expirationDate"], "%Y-%m-%d")
                    if exp_date > dt.now():
                        yield [user_json, self.counters]
                    elif exp_date < dt.now() and (
                        self.get_current_checked_out(user_json) > 0
                        or float(user_json["fixedFields"]["96"]["value"]) > 0
                    ):
                        add_stats(self.counters, "expired_with_loans_or_money_owed")
                        yield [user_json, self.counters]
                    # Filter out Expired patrons
                    else:
                        add_stats(self.counters, "expired")
            except Exception as ee:
                print(ee)
                print(line)

    def create_blocks(self, user, folio_user):
        blockinfo = user.get("blockInfo", {}).get("code", "")
        codes = {"a": "check address", "m": "mobius block", "u": "unpaid bill"}
        if blockinfo in ["m", "u", "a"]:
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
            add_stats(self.counters, "no_emails")
            print("No emails attribute for {}".format(user["id"]))
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
            add_stats(self.counters, "no_emails")
            print("Zero emails for {}".format(user["id"]))
            return self.default_email
        else:
            eml = user["emails"][0]
            reg = r"[^@]+@[^@]+\.[^@]+"
            if not re.match(reg, eml):
                add_stats(self.counters, "invalid_email")
                print("email likely invalid {} for user {}".format(eml, user["id"]))
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
                print(f"other barcode {barcode} for user {user['id']}")
        if other and not folio_barcode:
            print(f"Other barcode and no barcode for user {user['id']}")
        if other and not m_number:
            print(f"Other barcode and no m_number for user {user['id']}")
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
