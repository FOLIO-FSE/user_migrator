from datetime import datetime as dt
import datetime
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
        self.counters = {
            'expired': 0,
            'tot_checkedout': 0,
            'successful_checkedout': 0,
            'suppressed': 0,
            'blocked': 0,
            'deleted': 0,
            'illLibs': 0,
            'pMessage': {},
            'pMessage_count': 0,
            'missing_personnummer': 0,
            'incorrect_personnummer_recent': 0,
            'no_emails': 0,
            'invalid_email': 0,
            'more_than_one_emails': 0,
            'too_many_personnummer': 0,
            'incorrect_personnummer': 0,
            'total2': 0,
            "incorrect_personnummer_checkouts": 0,
            'missing_cid': 0,
            'incorrect_cid_checkouts': 0
        }

    def do_map(self, user):
        checked_out = self.get_current_checked_out(user)
        self.counters['tot_checkedout'] += checked_out
        new_user = {"id": str(uuid.uuid4()),
                    "patronGroup": str(user['patronType']),
                    "barcode": re.sub('\s+', '', self.get_barcode(user)).strip(),
                    "username": re.sub('\s+', '', self.get_user_name(user)).strip(),
                    "externalSystemId": re.sub('\s+', '', self.get_ext_uid(user)).strip(),
                    "active": self.get_active(user),
                    "personal": {"preferredContactTypeId": "email",
                                 "lastName": self.get_names(user)[0],
                                 "firstName": self.get_names(user)[1],
                                 "phone": '',  # No phones!
                                 "email": self.get_email(user),
                                 # "email": 'ttolstoy@ebsco.com',
                                 "addresses": self.get_addresses(user)},
                    "expirationDate": user['expirationDate']}
        if not new_user['personal']["addresses"]:
            del new_user['personal']["addresses"]
        self.counters['successful_checkedout'] += checked_out
        return new_user, user['id']

    def get_users(self, source_file):
        for line in source_file:
            self.counters['total2'] += 1
            user_json = json.loads(line)
            try:
                # if user_json['id'] in ['1021461','1023445', '1132876']:
                #    print(user_json)
                if user_json['deleted'] is True:
                    self.counters['deleted'] += 1
                elif user_json['suppressed'] is True:
                    self.counters['suppressed'] += 1
                elif user_json['blockInfo']['code'] != '-':
                    self.counters['blocked'] += 1
                else:
                    if user_json['pMessage'].strip() != '':
                        self.counters['pMessage_count'] += 1
                        if user_json['pMessage'] not in self.counters['pMessage']:
                            self.counters['pMessage'][user_json['pMessage']] = 1
                        else:
                            self.counters['pMessage'][user_json['pMessage']] += 1
                    exp_date = dt.strptime(
                        user_json['expirationDate'], '%Y-%m-%d')
                    if exp_date > dt.now():
                        yield[user_json, self.counters]
                    else:
                        self.counters['expired'] += 1
            except Exception as ee:
                print(ee)
                print(line)

    def get_email(self, user):
        default_email = 'support.lib@chalmers.se'
        if 'emails' not in user:
            self.counters['no_emails'] += 1
            print("No emails attribute for {}".format(user['id']))
            return default_email
        elif len(user['emails']) > 1:
            self.counters['more_than_one_emails'] += 1
            print("Too many emails for {}".format(user['id']))
            return user['emails'][0]
        elif not user['emails']:
            self.counters['no_emails'] += 1
            print("Zero emails for {}".format(user['id']))
            return default_email
        else:
            eml = user['emails'][0]
            reg = r"[^@]+@[^@]+\.[^@]+"
            if not re.match(reg, eml):
                self.counters['invalid_email'] += 1
                print("email likely invalid {} for user {}"
                      .format(eml, user['id']))
                return default_email
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
                return user['barcodes'][0].lower()
        else:
            raise ValueError("No barcodes for  {}".format(user['id']))

    def get_personnummer(self, user):
        # Public library
        if user['patronType'] in [110, 120, 130, 140, 150, 200, 201]:
            return self.get_barcode(user)
        # All other users
        elif 'uniqueIds' not in user:
            self.counters['missing_personnummer'] += 1
            raise ValueError("no uniqueIds attrib for {}"
                             .format(user['id']))
        elif len(user['uniqueIds']) > 1:
            self.counters['too_many_personnummer'] += 1
            raise ValueError("Too many unique ids for {}"
                             .format(user['id']))
        elif not user['uniqueIds']:
            self.counters['missing_personnummer'] += 1
            raise ValueError("Zero uniqueIds for {}"
                             .format(user['id']))
        else:
            uid = str(user['uniqueIds'][0]).replace('-', '').strip()
            if len(uid) == 10:
                # print(uid)
                return uid
            else:
                created_date = dt.strptime(
                    user['createdDate'], '%Y-%m-%dT%H:%M:%SZ')
                months_back = (dt.now() - datetime.timedelta(6 * 365 / 12))
                # recent user without swedish personnummer
                if created_date < months_back:
                    self.counters['incorrect_personnummer_recent'] += 1
                    print("Recently added {} patron with invalid swedish personnummer. Adding despite malformed uniqueid {}"
                          .format(created_date, uid))
                    return uid
                if self.get_current_checked_out(user) > 0:
                    self.counters['incorrect_personnummer_checkouts'] += 1
                    print("Patron with loans. Adding despite malformed uniqueid {}"
                          .format(uid))
                    return uid
                self.counters['incorrect_personnummer'] += 1
                raise ValueError("Incorrect personnummer ({}) for user {}?"
                                 .format(uid, user['id']))

    def get_user_name(self, user):
        return self.get_personnummer(user)

    def get_current_checked_out(self, user):
        return int(user['fixedFields']["50"]["value"])

    def get_ext_uid(self, user):
        cid = next((vf['content'] for vf in user['varFields']
                    if 'e' in vf['fieldTag']), '')
        if user['patronType'] in [10, 11, 19, 20, 30]:
            # User is chalmers affiliated and should use CID
            if not cid:
                self.counters['missing_cid'] += 1
                if user['patronType'] in [10, 11, 19, 20]:
                    if self.get_current_checked_out(user) > 0:
                        self.counters['incorrect_cid_checkouts'] += 1
                        raise ValueError("Patron {} has loans but no CID"
                                         .format(user['id']))
                    else:
                        raise ValueError("No cid for user {}, and patronType is {}. Skipping"
                                         .format(user['id'], user['patronType']))
                else:
                    print(
                        "GU-student {} utan CID. TIlldelar barcode".format(user['id']))
                    return self.get_barcode(user)
            return cid + '@chalmers.se'
        elif user['patronType'] in [110, 120, 130, 140, 150, 200, 201]:
            barcode = self.get_barcode(user)
            # print("PUBLIC LIBRARY: {} of type{}".format(barcode, user['patronType']))
            return barcode
        elif user['patronType'] in [30, 50, 60]:
            # User is considered member of public. Barcode.
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
        elif not user['names']:
            raise ValueError("Zero names for {}".format(user['id']))
        elif ', ' not in user['names'][0]:
            if user['patronType'] not in [110, 120, 130, 140, 150, 200, 201]:
                raise ValueError("No comma in name for {}".format(user['id']))
            return [user['names'][0], '']
        else:
            return user['names'][0].split(', ')

    def get_expiration_date(self, user):
        return user['expirationDate']

    def get_addresses(self, user):
        # TODO: For organizations, add institution as address type
        # TODO: map addresses better
        if user['patronType'] in [110, 120, 130, 140, 150, 200, 201]:
            if 'addresses' not in user:
                raise ValueError(
                    "no addresses attrib for {}".format(user['id']))
            num_adr = len(user['addresses'])
            if num_adr == 0:
                raise ValueError("0 addresses for {}".format(user['id']))
            if num_adr > 2:
                print("Too many addresses for {}. Taking the first"
                      .format(user['id']))
            else:
                if num_adr == 1:
                    adr = self.parse_address(user['addresses'][0])
                    adr['addressTypeId'] = 'Address 1'
                    adr['primaryAddress'] = True
                    return [adr]
                elif num_adr == 2:
                    adr_1 = self.parse_address(user['addresses'][0])
                    adr_1['addressTypeId'] = 'Address 1'
                    adr_1['primaryAddress'] = True
                    adr_2 = self.parse_address(user['addresses'][1])
                    adr_2['addressTypeId'] = 'Address 2'
                    adr_2['primaryAddress'] = False
                    return [adr_1, adr_2]

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
