from datetime import datetime as dt
import re
import uuid
import requests
import csv
import io
import json


class Chalmers:
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

    def do_map(self, user):
        new_user = {"id": str(uuid.uuid4()),
                    "patronGroup": str(user['patronType']),
                    "barcode": self.get_barcode(user),
                    "username": self.get_user_name(user),
                    "externalSystemId": self.get_ext_uid(user),
                    "active": self.get_active(user),
                    "personal": {"preferredContactTypeId": "mail",
                                 "lastName": self.get_names(user)[0],
                                 "firstName": self.get_names(user)[1],
                                 "phone": '',  # No phones!
                                # "email": self.get_email(user),
                                 "email": 'ttolstoy@ebsco.com',
                                 "addresses": self.get_addresses(user)},
                    "expirationDate": user['expirationDate']}
        if not new_user['personal']["addresses"]:
            del new_user['personal']["addresses"]
        return new_user, user['id']

    def get_users(self, source_file):
        counters = {'expired': 0,
                    'suppressed': 0,
                    'blocked': 0,
                    'deleted': 0,
                    'illLibs': 0,
                    'pMessage': 0,
                    'total2': 0}
        for line in source_file:
            counters['total2'] += 1
            user_json = json.loads(line)
            if user_json['deleted'] is True:
                counters['deleted'] += 1
            elif user_json['suppressed'] is True:
                counters['suppressed'] += 1
            elif user_json['blockInfo']['code'] != '-':
                counters['blocked'] += 1
            elif user_json['pMessage'].strip() != '':
                counters['pMessage'] += 1
            else:
                exp_date = dt.strptime(user_json['expirationDate'], '%Y-%m-%d')
                if exp_date > dt.now():
                    yield[user_json, counters]
                else:
                    counters['expired'] += 1

    def get_email(self, user):
        if 'emails' not in user:
            raise ValueError("No emails attribute for {}".format(user['id']))
        elif len(user['emails']) > 1:
            raise ValueError("Too many emails for {}".format(user['id']))
        elif not user['emails']:
            raise ValueError("Zero emails for {}".format(user['id']))
        else:
            eml = user['emails'][0]
            reg = r"[^@]+@[^@]+\.[^@]+"
            if not re.match(reg, eml):
                raise ValueError("email likely invalid {} for user {}"
                                 .format(eml, user['id']))
            else:
                return eml

    def get_barcode(self, user):
        if 'barcodes' in user:
            if len(user['barcodes']) > 1:
                raise ValueError("Too many barcodes for {}"
                                 .format(user['id']))
            elif not user['barcodes']:
                raise ValueError("Zero barcodes for {}"
                                 .format(user['id']))
            else:
                return user['barcodes'][0]
        else:
            raise ValueError("No barcodes for  {}".format(user['id']))

    def get_personnummer(self, user):
        if 'uniqueIds' not in user:
            raise ValueError("no uniqueIds attrib for {}"
                             .format(user['id']))
        elif len(user['uniqueIds']) > 1:
            raise ValueError("Too many unique ids for {}"
                             .format(user['id']))
        elif not user['uniqueIds']:
            raise ValueError("Zero uniqueIds for {}"
                             .format(user['id']))
        else:
            uid = str(user['uniqueIds'][0]).replace('-', '').strip()
            if len(uid) == 10:
                # print(uid)
                return uid
            else:
                raise ValueError("Incorrect personnummer ({}) for user {}?"
                                 .format(uid, user['id']))

    def get_user_name(self, user):
        return self.get_personnummer(user)

    def get_ext_uid(self, user):
        cid = next((vf['content'] for vf in user['varFields']
                    if 'e' in vf['fieldTag']), '')
        if user['patronType'] in [10, 11, 19, 20, 30]:
            # User is chalmers affiliated and should use CID
            if not cid:
                if user['patronType'] in [10, 11, 19, 20]:
                    raise ValueError("No cid for user {}, and patronType is {}. Skipping"
                                     .format(user['id'], user['patronType']))
                else:
                    print("GU-student {} utan CID. TIlldelar barcode".format(user['id']))
                    return self.get_barcode(user)
            return cid+ '@chalmers.se'
        elif user['patronType'] in [110, 120, 130, 140, 150, 200, 201]:
            # User is library and should use library code
            barcode = self.get_barcode(user)
            print("PUBLIC LIBRARY: {}".format(barcode))
            print(user)
            return barcode
        elif user['patronType'] in [30, 50, 60]:
            # User is considered member of public. Barcode.
            return self.get_barcode(user)
        else:
            raise ValueError("Unhandled patronType {} for {}"
                             .format(user['patronType'], user['id']))

    def get_active(self, user):
        return True

    def get_names(self, user):
        if 'names' not in user:
            raise ValueError("no names attrib for {}".format(user['id']))
        if len(user['names']) > 1:
            raise ValueError("Too many names for {}".format(user['id']))
        elif not user['names']:
            raise ValueError("Zero names for {}".format(user['id']))
        elif ', ' not in user['names'][0]:
            raise ValueError("No comma in name for {}".format(user['id']))
        else:
            return user['names'][0].split(', ')

    def get_expiration_date(self, user):
        return user['expirationDate']

    def get_addresses(self, user):
        # TODO: For organizations, add institution as address type
        # TODO: map addresses better
        if user['patronType'] in [110, 120, 130, 140, 150, 200, 201]:
            inst_id = 'Library address'
            if 'addresses' not in user:
                raise ValueError("no addresses attrib for {}".format(user['id']))
            num_adr = len(user['addresses'])
            if num_adr == 0:
                raise ValueError("0 addresses for {}".format(user['id']))
            elif num_adr > 2:
                raise ValueError("Too many addresses for {}".format(user['id']))
            else:
                if num_adr == 1:
                    adr = self.parse_address(user['addresses'][0])
                    adr['addressTypeId'] = inst_id
                    adr['primaryAddress'] = True
                    return [adr]
                elif num_adr == 2:
                    adr_home = self.parse_address(user['addresses'][0])
                    adr_home['addressTypeId'] = inst_id
                    adr_home['primaryAddress'] = False
                    adr_inst = self.parse_address(user['addresses'][1])
                    adr_inst['addressTypeId'] = inst_id
                    adr_inst['primaryAddress'] = True
                    return [adr_home, adr_inst]

    def parse_address(self, address):
        lines = address['lines']
        return {"countryId": '',
                "addressTypeId": '',
                "addressLine1": lines[0] if lines else '',
                "addressLine2": ' '.join(lines[1:]) if len(lines) > 1 else '',
                "region": '',
                "city": '',
                "primaryAddress": '',
                "postalCode": ''}


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
