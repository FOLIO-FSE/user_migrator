import re
import uuid
import requests
import csv
import io
import json


class Alabama:

    def __init__(self, config):
        self.groupsmap = config["groupsmap"]
        country_codes_url = ("https://raw.githubusercontent.com/"
                             "datasets/country-codes/master/data/"
                             "country-codes.csv")
        req = requests.get(country_codes_url)
        self.country_data = list(csv.DictReader(io.StringIO(req.text)))

    def do_map(self, user):
        user = {"id": str(uuid.uuid4()),
                "patronGroup": self.get_group(user),
                "barcode": self.get_barcode(user),
                "username": self.get_user_name(user),
                "externalSystemId": self.get_ext_uid(user),
                "active": self.get_active(user),
                "personal": {"preferredContactTypeId": "mail",
                             "lastName": self.get_names(user)[0],
                             "firstName": self.get_names(user)[1],
                             "middleName": self.get_names(user)[2],
                             "phone": self.get_phone(user, 'Primary'),
                             "mobilePhone": self.get_phone(user, 'Mobile'),
                             "email": self.get_email(user),
                             "addresses": list(self.get_addresses(user))},
                "expirationDate": self.get_expiration_date(user)}
        return user, self.get_ext_uid(user)

    def get_users(self, source_file):
        return json.load(source_file)['patronList']['patron']

    def get_phones(self, user):
        has_temp = ('tempAddressList' in user and
                    'tempAddress' in user['tempAddressList'])
        t_addr_path = "patronPhoneList.patronPhone"
        if (has_temp):
            temp_addrs = find_multi("tempAddressList.tempAddress", user)
            for temp_addr in temp_addrs:
                phone_l = find(t_addr_path, temp_addr)
                if phone_l and isinstance(phone_l, (list,)):
                    for p in phone_l:
                        if re.sub(r"[()\-\s]", '', p['phone']):
                            yield p
                elif (phone_l and 'phone' in phone_l
                      and len(re.sub(r"[()\-\s]", '', phone_l['phone'])) > 1):
                    yield phone_l
                else:
                    yield None
        else:
            return []

    def get_phone(self, user, kind):
        try:
            ps = self.get_phones(user)
            return next((p['phone'] for p in ps if p['type'] == kind))
        except Exception as ee:
            print("No {} phone for user:\t{}".format(kind,
                                                     self.get_ext_uid(user)))

    def get_email(self, user):
        if 'emailList' in user:
            p_email = user['emailList']['patronEmail']
            if isinstance(p_email, (list,)):
                print("Multiple emails!")
                print(p_email)
                return p_email[0]['email']
            else:
                return p_email['email']
        else:
            return ''

    def get_group(self, user):
        b = self.get_correct_barcode_struct(user)
        code = next(g['Folio Code'] for g
                    in self.groupsmap
                    if g['ILS code'] == b["patronGroup"])
        return code

    def get_barcode(self, user):
        b = self.get_correct_barcode_struct(user)
        return (b["barcode"] if 'barcode' in b else '')

    def bc_is_correct(self, barcode):
        if len(barcode) == 16 and barcode.startswith('6'):
            return True
        elif len(barcode) == 9:
            return True
        else:
            return False

    def get_correct_barcode_struct(self, user):
        b = user['patronBarcodeList']['patronBarcode']
        if isinstance(b, (list,)):
            b_sort = sorted(b,
                            key=lambda x: x['barcodeModifiedDate'],
                            reverse=True)
            return next(bc for bc in b_sort
                        if(self.bc_is_correct(bc['barcode'])
                           and bc['barcodeStatus'] == 'Active'))
        elif isinstance(b, (dict,)) and self.bc_is_correct(b['barcode']):
            return b
        else:
            print(b)
            return b

    def get_user_name(self, user):
        email = self.get_email(user).split('@')
        if len(email) > 1 and 'ua.edu' in email[1]:
            return email[0]
        else:
            print('Not an UA address: {}'.format(email))
            return email[0]

    def get_ext_uid(self, user):
        return str(uuid.uuid4())
        # return user['institutionID']

    def get_active(self, user):
        b = self.get_correct_barcode_struct(user)
        if 'barcodeStatus' in b:
            return b['barcodeStatus'] == 'Active'
        else:
            print("No bcs!")
            return False

    def get_names(self, user):
        return ((user['lastName'] if 'lastName' in user
                 else ''),
                (user['firstName'] if 'firstName' in user
                else ''),
                (user['middleName'] if 'middleName' in user
                 else ''))

    def get_expiration_date(self, user):
        return user['expirationDate']

    def get_addresses(self, user):
        has_temp_addr = False
        if 'tempAddressList' in user:
            has_temp_addr = True
            temp_addrs = find_multi("tempAddressList.tempAddress", user)
            t_addr = next(t for t in temp_addrs)
            yield {"countryId": '',
                   "addressTypeId": "Home",
                   "addressLine1": (t_addr['line1'] if 'line1' in t_addr
                                    else ''),
                   "addressLine2": ((t_addr['line2'] if 'line2' in t_addr
                                    else '') +
                                    (t_addr['line3'] if 'line3' in t_addr
                                     else '')),
                   "region": (t_addr['stateProvince']
                              if 'stateProvince' in t_addr else ''),
                   "city": (t_addr['city'] if 'city' in t_addr
                            else ''),
                   "primaryAddress": True,
                   "postalCode": (t_addr['postalCode']
                                  if 'postalCode' in t_addr else '')}

        p_addr = user['permAddress']
        yield {"countryId": '',
               "addressTypeId": "Campus",
               "addressLine1": (p_addr['line1'] if 'line1' in p_addr else ''),
               "addressLine2": ((p_addr['line2'] if 'line2' in p_addr
                                 else '') +
                                (p_addr['line3'] if 'line3' in p_addr
                                 else '')),
               "region": (p_addr['stateProvince']
                          if 'stateProvince' in p_addr else ''),
               "city": (p_addr['city'] if 'city' in p_addr else ''),
               "primaryAddress": not has_temp_addr,
               "postalCode": (p_addr['postalCode']
                              if 'postalCode' in p_addr else '')}


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


def find_multi(element, json):
    keys = element.split('.')
    rv = json
    for key in keys:
        rv = rv[key]
    if isinstance(rv, (list,)):
        return rv
    else:
        yield rv
