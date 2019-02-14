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
                                  "email": self.get_email(user),
                                  "addresses": list(self.get_addresses(user))},
                     "expirationDate": user['expirationDate']}
        return new_user, user['id']

    def get_users(self, source_file):
        counters = { 'expired': 0,
                     'suppressed': 0,
                     'blocked': 0,
                     'deleted': 0 }
        for line in source_file:
            user_json = json.loads(line)
            if user_json['deleted'] == True:
                counters['deleted'] += 1
            elif user_json['suppressed'] == True:
                counters['suppressed'] += 1
            elif user_json['blockInfo']['code'] != '-':
                counters['blocked'] += 1
            else:
                exp_date = dt.strptime(user_json['expirationDate'], '%Y-%m-%d') 
                # exp_date = dateutil.parser.parse(user_json['expirationDate']) 
                if exp_date > dt.now():
                    yield[user_json, counters]
                else:
                    counters['expired'] += 1

    def get_email(self, user):
        if not 'emails' in user:
            raise ValueError("No emails attribute for {}".format(user['id']))
        elif len(user['emails']) > 1:
            raise ValueError("Too many emails for {}".format(user['id']))
        elif len(user['emails']) == 0:
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
            elif len(user['barcodes']) == 0:
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
        elif len(user['uniqueIds']) == 0:
            raise ValueError("Zero uniqueIds for {}"
                             .format(user['id']))
        else:
            uid = user['uniqueIds'][0]
            if len(uid) == 10:
                # print(uid)
                return uid
            else:
                raise ValueError("Incorrect personnummer ({}) for user {}?"
                                 .format(uid, user['id']))

    def get_user_name(self, user):
        return self.get_personnummer(user)

    def get_ext_uid(self, user):
        if user['patronType'] in [10, 11, 19, 20, 30]:
            # User is chalmers affiliated and should use CID
            email = self.get_email(user)
            if 'chalmers.se' not in self.get_email(user):
                raise ValueError("Not a propers CID ({}) for {}"
                                 .format(email, user['id']))
            return email
        elif user['patronType'] in [110, 120, 130, 140, 150, 200, 201]:
            # User is library and should use library code
            print(user)
        elif user['patronType'] in [30, 50, 60]:
            # User is considered member of public. Personnummer.
            return self.get_personnummer(user)
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
        elif len(user['names']) == 0:
            raise ValueError("Zero names for {}".format(user['id']))
        elif ', ' not in user['names'][0]:
            raise ValueError("No comma in name for {}".format(user['id']))
        else:
           return user['names'][0].split(', ')

    def get_expiration_date(self, user):
        return user['expirationDate']

    def get_addresses(self, user):
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
                adr['addressTypeId'] = '2400fbeb-b369-45f3-8de0-362ce5d114a4'
                adr['primaryAddress'] = True
                return [adr]
            elif num_adr == 2:
                adr_inst = self.parse_address(user['addresses'][0])
                adr_inst['addressTypeId'] = '6731169b-90e3-4dfe-8403-948c4432c3fc'
                adr_inst['primaryAddress'] = True
                adr_home = self.parse_address(user['addresses'][1])
                adr_home['addressTypeId'] = '2400fbeb-b369-45f3-8de0-362ce5d114a4'
                adr_home['primaryAddress'] = False
                return [adr_home, adr_inst]

    def parse_address(self, address):
        ls = address['lines']
        return {"countryId": '',
                "addressTypeId": '',
                "addressLine1": ls[0] if len(ls) > 0 else '',
                "addressLine2": ls[1] if len(ls) > 1 else '',
                "addressLine3": ' '.join(ls[2:]) if len(ls) > 2 else '',
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
