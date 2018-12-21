import re
import uuid
import requests
import csv
import io


class AlabamaBanner:

    def __init__(self, config):
        self.groupsmap = config["groupsmap"]
        country_codes_url = ("https://raw.githubusercontent.com/"
                             "datasets/country-codes/master/data/"
                             "country-codes.csv")
        req = requests.get(country_codes_url)
        self.country_data = list(csv.DictReader(io.StringIO(req.text)))

    def lpos(self, start, end, string):
        return string[int(start-1):int(end)].strip()

    def do_map(self, line):
        phone1 = self.lpos(776, 800, line),
        phone2 = self.lpos(1205, 1229, line),
        mobile1 = self.lpos(801, 825, line),
        mobile2 = self.lpos(1229, 1253, line),
        if self.is_student(line):
            phone = phone1
            mobile = mobile1
        else:
            phone = phone2
            mobile = mobile2

        user = {"id": str(uuid.uuid4()),
                "patronGroup": self.get_group(self.lpos(46, 55, line)),
                "barcode": self.lpos(21, 45, line),
                "username": self.lpos(1347, 1396, line).split('@')[0],
                "externalSystemId": self.lpos(239, 268, line),
                "active": self.lpos(56, 56, line) == "1",
                "personal": {"preferredContactTypeId": "mail",
                             "lastName": self.lpos(311, 340, line),
                             "firstName": self.lpos(341, 360, line),
                             "middleName": self.lpos(361, 380, line),
                             "phone": phone[0],
                             "mobilePhone": mobile[0],
                             "email": self.lpos(1347, 1396, line),
                             "addresses": list(self.get_addresses(line))},
                "expirationDate": self.lpos(189, 198, line).replace('.','-')}

        return user

    def is_student(self, line):
        group = self.get_group(self.lpos(46, 55, line))
        return (group in ['UNDERGRADUATE', 'GRADUATE'])

    def get_addresses(self, line):
        addr_type1 = self.lpos(467, 467, line),
        addr_code_status1 = self.lpos(467, 467, line),
        addr_type2 = self.lpos(896, 896, line),
        addr_code_status2 = self.lpos(897, 897, line),
        if addr_type1 == '1' and addr_code_status1 == 'N':
            addr1_is_primary = True
            addr2_is_primary = False
        else:
            addr1_is_primary = False
            addr2_is_primary = True
        if addr_type2 == '2' and addr_code_status2 == 'H':
            addr2_is_primary = False
            addr1_is_primary = True

        address1 = {"countryId": self.lpos(756, 775, line),
                    "addressTypeId": "",
                    "addressLine1": self.lpos(489, 538, line),
                    "addressLine2": "\n".join([self.lpos(539, 538, line),
                                               self.lpos(539, 578, line),
                                               self.lpos(579, 618, line),
                                               self.lpos(619, 658, line),
                                               self.lpos(659, 698, line)]),
                    "region": self.lpos(739, 745, line),
                    "city": self.lpos(699, 738, line),
                    "primaryAddress": addr1_is_primary,
                    "postalCode": self.lpos(746, 755, line)}
        address2 = {"countryId": self.lpos(1185, 1204, line),
                    "addressTypeId": self.lpos(896, 896, line),
                    "addressLine1": self.lpos(918, 967, line),
                    "addressLine2": "\n".join([self.lpos(968, 1007, line),
                                               self.lpos(1008, 1127, line)]),
                    "region": self.lpos(1168, 1174, line),
                    "city": self.lpos(1128, 1167, line),
                    "primaryAddress": addr2_is_primary,
                    "postalCode": self.lpos(1175, 1184, line)}
        return [address1, address2]

    def get_users(self, source_file):
        return source_file.readlines()

    def get_group(self, ils_code):
        return next((g['Folio Code'] for g
                     in self.groupsmap
                     if g['ILS code'] == ils_code), 'unmapped')

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
