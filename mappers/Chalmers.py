import uuid
import requests
import csv
import io
import json


class Chalmers:

    def __init__(self, config):
        self.groupsmap = config["groupsmap"]
        country_codes_url = ("https://raw.githubusercontent.com/"
                             "datasets/country-codes/master/data/"
                             "country-codes.csv")
        req = requests.get(country_codes_url)
        self.country_data = list(csv.DictReader(io.StringIO(req.text)))

    def do_map(self, user):
        return {"id": str(uuid.uuid4()),
                "patronGroup": user['patronType'],
                "barcode": self.get_barcode(user),
                "username": self.get_user_name(user),
                "externalSystemId": self.get_ext_uid(user),
                "active": self.get_active(user),
                "personal": {"preferredContactTypeId": "mail",
                             "lastName": '',
                             "firstName": '',
                             "phone": self.get_phone(user),
                             "email": self.get_email(user),
                             "addresses": list(self.get_addresses(user))},
                "expirationDate": user['expirationDate']}

    def get_users(self, source_file):
        for line in source_file:
            yield json.loads(line)

    def get_phone(self, user):
        return ''

    def get_email(self, user):
        return ''

    def get_barcode(self, user):
        return ''

    def get_user_name(self, user):
        return ''

    def get_ext_uid(self, user):
        return ''

    def get_active(self, user):
        return False

    def get_names(self, user):
        return ''

    def get_expiration_date(self, user):
        return ''

    def get_addresses(self, user):
        if 'addresses' not in user:
            return []
        for a in user['addresses']:
            ls = a['lines']
            yield {"countryId": '',
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
