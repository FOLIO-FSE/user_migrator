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
        country_codes_url = ("https://raw.githubusercontent.com/"
                             "datasets/country-codes/master/data/"
                             "country-codes.csv")
        req = requests.get(country_codes_url)
        self.country_data = list(csv.DictReader(io.StringIO(req.text)))
        self.default_email = 'ttolstoy@ebsco.com'
        self.counters = {}
        self.counters['pmessage_counts'] = {}
        self.counters['blockinfo'] = {}

    def do_map(self, user):
        checked_out = self.get_current_checked_out(user)
        add_stats(self.counters, 'tot_checkedout', checked_out)
        new_user = {"username": self.get_username(user),
                    "id": str(uuid.uuid4()),
                    "externalSystemId": re.sub('\s+', '', self.get_ext_uid(user)).strip(),
                    "barcode": re.sub('\s+', '', self.get_barcode(user)).strip(),
                    "patronGroup": str(user['patronType']),
                    "active": self.get_active(user),
                    "personal": {"lastName": self.get_names(user)[0],
                                 "firstName": self.get_names(user)[1],
                                 # "middleName":
                                 "preferredContactTypeId": "email",
                                 "phone": '',  # No phones!
                                 #  "mobilePhone":
                                 # "dateOfBirth":
                                 # "email": self.get_email(user),
                                 "email": 'ttolstoy@ebsco.com',
                                 #  "enrollmentDate":
                                 # "addresses": list(self.get_addresses(user))
                                 },
                    "expirationDate": user['expirationDate'],
                    "type": "object"}
        # if not new_user['personal']["addresses"]:
        #    del new_user['personal']["addresses"]
        add_stats(self.counters, 'successful_checkedout', checked_out)
        return new_user, user['id']

    def get_users(self, source_file):
        for line in source_file:
            add_stats(self.counters, 'total2')
            user_json = json.loads(line)
            try:
                # if user_json['id'] in ['1021461','1023445', '1132876']:
                #    print(user_json)
                # Filter out deleted users
                if user_json['deleted'] is True:
                    add_stats(self.counters, 'deleted')
                # Filter out suppressed patrons
                elif user_json['suppressed'] is True:
                    add_stats(self.counters, 'suppressed')
                # Filter out blocked patrons
                # elif user_json['blockInfo']['code'] != '-':
                #     add_stats(self.counters, 'blocked')
                else:
                    add_stats(self.counters['blockinfo'],
                              user_json['blockInfo']['code'])
                    if user_json['pMessage'].strip() != '':
                        add_stats(self.counters, 'pMessage_count')
                        add_stats(
                            self.counters['pmessage_counts'],
                            user_json['pMessage'])
                    exp_date = dt.strptime(
                        user_json['expirationDate'], '%Y-%m-%d')
                    if exp_date > dt.now():
                        yield [user_json, self.counters]
                    # Expired patrons with open loans are brought over
                    elif (exp_date < dt.now()
                          and self.get_current_checked_out(user_json) > 0):
                        add_stats(self.counters, 'expired_with_loans')
                        yield [user_json, self.counters]
                    # Filter out Expired patrons
                    else:
                        add_stats(self.counters, 'expired')
            except Exception as ee:
                print(ee)
                print(line)

    def get_username(self, user):
        uname = self.get_email(user)
        if uname == self.default_email:
            add_stats(self.counters, 'uuid_user_name')
            return str(uuid.uuid4())
        return uname

    def get_email(self, user):
        if 'emails' not in user:
            add_stats(self.counters, 'no_emails')
            print("No emails attribute for {}".format(user['id']))
            return self.default_email
        elif len(user['emails']) > 1:
            add_stats(self.counters, 'more_than_one_emails')
            print("Too many emails for {}".format(user['id']))
            return user['emails'][0]
        elif not user['emails']:
            add_stats(self.counters, 'no_emails')
            print("Zero emails for {}".format(user['id']))
            return self.default_email
        else:
            eml = user['emails'][0]
            reg = r"[^@]+@[^@]+\.[^@]+"
            if not re.match(reg, eml):
                add_stats(self.counters, 'invalid_email')
                print("email likely invalid {} for user {}"
                      .format(eml, user['id']))
                return self.default_email
            else:
                return eml

    def get_barcode(self, user):
        if 'barcodes' in user:
            if len(user['barcodes']) > 1:
                for b in user['barcodes']:
                    if not b.startswith('M'):
                        return b
            elif not user['barcodes']:
                raise ValueError("Zero barcodes for {}"
                                 .format(user['id']))
            else:
                uniques = user.get('uniqueIds', [])
                for uid in uniques:
                    if uid..startswith('M'):
                        add_stats(self.counters, 'single_barcode_unique_M')
                if user['barcodes'][0].startswith('M'):
                    add_stats(self.counters, 'single_barcode_with_M')
                elif user['barcodes'][0].startswith('m'):
                    add_stats(self.counters, 'single_barcode_with_m')
                else:
                    add_stats(self.counters, 'single_barcode_without_m')
                return user['barcodes'][0].lower()
        else:
            raise ValueError("No barcodes for  {}".format(user['id']))

    def get_current_checked_out(self, user):
        return int(user['fixedFields']["50"]["value"])

    def get_ext_uid(self, user):

        if 'barcodes' in user:
            if len(user['barcodes']) > 1:
                for b in user['barcodes']:
                    if b.startswith('M'):
                        add_stats(self.counters, 'ext_id_barcode')
                        return f"BARCODE:{b}"
        else:
            ids = user.get('uniqueIds', [])
            if len(ids) == 0:
                print(f"No uniqueIds for {user['id']}")
            elif len(ids) == 1:
                add_stats(self.counters, 'ext_id_unique_id')
                f"UNIQUEID:{ids[0]}"
            elif len(ids) > 1:
                print(f"more than one uniqueIds for {user['id']}")
                add_stats(self.counters, 'ext_id_unique_id')
                return f"UNIQUEID:{ids[0]}"
        return ''

    def get_active(self, user):
        return True

    def get_names(self, user):
        if 'names' not in user:
            raise ValueError(f"no names attrib for {user['id']}")
        if len(user['names']) > 1:
            raise ValueError(f"Too many names for {user['id']}")
        elif not user['names']:
            raise ValueError(f"Zero names for {user['id']}")
        elif ', ' not in user['names'][0]:
            if user['patronType'] not in [110, 120, 130, 140, 150, 200, 201]:
                raise ValueError(f"No comma in name for {user['id']}")
            return [user['names'][0], '']
        else:
            return user['names'][0].split(', ')

    def get_expiration_date(self, user):
        return user['expirationDate']

    def get_addresses(self, user):
        # TODO: For organizations, add institution as address type
        # TODO: map addresses better
        if 'addresses' not in user:
            print(f"no addresses attrib for {user['id']}")
        else:
            num_adr = len(user['addresses'])
            if num_adr == 0:
                print(f"0 addresses for {user['id']}")
            if num_adr > 2:
                print(f"{num_adr} addresses for {user['id']}")
            else:
                h_adr = next((a for a in user['addresses']
                              if a['type'] == 'h' and any(a['lines'])), None)
                a_adr = next((a for a in user['addresses']
                              if a['type'] == 'a' and any(a['lines'])), None)
                if h_adr:
                    adr = self.parse_address(h_adr)
                    adr['addressTypeId'] = 'Home'
                    adr['primaryAddress'] = True
                    yield adr
                if a_adr:
                    adr = self.parse_address(a_adr)
                    adr['addressTypeId'] = 'Work'
                    adr['primaryAddress'] = True
                    yield adr

    def parse_address(self, address):
        lines = address['lines']
        return {"countryId": '',
                "addressTypeId": '',
                "addressLine1": lines[0] if lines else '',
                "addressLine2": ' '.join(lines[1:]) if len(lines) > 1 else '',
                "region": '',
                "city": '',
                "primaryAddress": '',
                "postalCode": ''
                }


def gen_dict_extract(key, var):
    if hasattr(var, 'iteritems'):
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
    keys = element.split('.')
    rv = json
    for key in keys:
        rv = rv[key]
        return rv


def add_stats(stats, a, value=1):
    if a not in stats:
        stats[a] = value
    else:
        stats[a] += value


def validate(stats_map, folio_object, ):
    for key, value in folio_object.items():
        if isinstance(value, str) and any(value):
            add_stats(stats_map, key)
        if isinstance(value, list) and any(value):
            add_stats(stats_map, key)
