import uuid
import requests
import csv
import io
import json


class Alabama:

    states = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA",
              "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
              "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
              "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
              "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]

    def __init__(self, config):
        self.groupsmap = config["groupsmap"]
        country_codes_url = ("https://raw.githubusercontent.com/"
                             "datasets/country-codes/master/data/"
                             "country-codes.csv")
        req = requests.get(country_codes_url)
        self.country_data = list(csv.DictReader(io.StringIO(req.text)))

    def do_map(self, user):
        return {"id": str(uuid.uuid4()),
                "patronGroup": self.get_group(user),
                "barcode": self.get_barcode(user),
                "username": self.get_user_name(user),
                "externalSystemId": self.get_ext_uid(user),
                "active": self.get_active(user),
                "personal": {"preferredContactTypeId": "mail",
                             "lastName": self.get_names(user)[0],
                             "firstName": self.get_names(user)[1],
                             "phone": self.get_phone(user),
                             "email": self.get_email(user),
                             "addresses": list(self.get_addresses(user))},
                "expirationDate": self.get_expiration_date(user)}

    def get_users(self, source_file):
        return json.load(source_file)['patronList']['patron']

    def get_phone(self, user):
        has_temp = 'tempAddressList' in user
        t_addr_path = "tempAddressList.tempAddress"
        if (has_temp and 'patronPhoneList' in find(t_addr_path, user)):
            t_addr = find(t_addr_path, user)
            phone_l = t_addr['patronPhoneList']['patronPhone']
            if isinstance(phone_l, (list,)):
                return phone_l[0]['phone']
            elif 'phone' in phone_l:
                return phone_l['phone']
            else:
                print(phone_l)
        else:
            return ''

    def get_email(self, user):
        if 'emailList' in user:
            p_email = user['emailList']['patronEmail']
            if isinstance(p_email, (list,)):
                return p_email[0]['email']
            else:
                return p_email['email']
        else:
            return ''

    def get_group(self, user):
        b = self.get_correct_barcode_struct(user)
        return (b["patronGroup"] if 'patronGroup' in b else '')

    def get_barcode(self, user):
        b = self.get_correct_barcode_struct(user)
        return (b["barcode"] if 'barcode' in b else '')

    def get_correct_barcode_struct(self, user):
        b = user["patronBarcodeList"]['patronBarcode']
        if isinstance(b, (list,)):
            return b[0]
        elif isinstance(b, (dict,)):
            return b
        else:
            print(b)
            return b

    def get_user_name(self, user):
        return user['patronId']

    def get_ext_uid(self, user):
        return user['patronId']

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
                else ''))

    def get_expiration_date(self, user):
        return user['expirationDate']

    def get_addresses(self, user):
        has_temp_addr = False
        if 'tempAddressList' in user:
            has_temp_addr = True
            t_addr = user['tempAddressList']['tempAddress']
            yield {"countryId": '',
                   "addressTypeId": "Home",
                   "addressLine1": (t_addr['line1'] if 'line1' in t_addr
                                    else ''),
                   # "addressLine2": t_addr['line2'],
                   # "addressLine3": t_addr['line3'],
                   "region": (t_addr['stateProvince']
                              if 'stateProvince' in t_addr else ''),
                   "city": (t_addr['city'] if 'city' in t_addr
                            else ''),
                   "primaryAddress": True,
                   "postalCode": (t_addr['postalCode']
                                  if 'postalCode' in t_addr else '')}

        p_addr = user['permAddress']
        yield {"countryId": '',
               "addressTypeId": "Home",
               "addressLine1": (p_addr['line1'] if 'line1' in p_addr else ''),
               # "addressLine2": p_addr['line2'],
               # "addressLine3": p_addr['line3'],
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
