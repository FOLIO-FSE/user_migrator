import json
import usaddress
from datetime import datetime
import uuid
import requests
import csv
import io


class FiveColleges:

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

    def get_users(self, source_file):
        for patron in json.load(source_file)["p-file-20"]["patron-record"]:
            yield [patron, None]

    def do_map(self, aleph_user):
        return {"id": str(uuid.uuid4()),
                "patronGroup": self.get_group(aleph_user),
                "barcode": self.get_barcode(aleph_user),
                "username": self.get_user_name(aleph_user),
                "externalSystemId": self.get_ext_uid(aleph_user),
                "active": self.get_active(aleph_user),
                "personal": {"preferredContactTypeId": "mail",
                             "lastName": self.get_names(aleph_user)[0],
                             "firstName": self.get_names(aleph_user)[1],
                             "phone": self.get_phone(aleph_user),
                             "email": "aarnold@ebsco.com", # self.get_email(aleph_user),
                             "addresses": list(self.get_addresses(aleph_user))},
                "expirationDate": self.get_expiration_date(aleph_user)}

    def get_group(self, aleph_user):
        z305 = self.get_z305(aleph_user)
        if 'z305-bor-status' in z305:
            a_group = z305['z305-bor-status']
        elif 'bor-status' in z305:
            a_group = z305['bor-status']
        else:
            raise ValueError("No group for user {}"
                             .format(self.get_ext_uid(aleph_user)))
        return a_group

    def get_email(self, aleph_user):
        z304s = self.get_z304(aleph_user)
        email = next((z304['z304-email-address'] for z304
                      in z304s
                      if z304['z304-email-address']), None)
        if not email:
            # five collages do not want email failing.
            # raise ValueError("No email address for {}"
            #                 .format(self.get_user_name(aleph_user)))
            return ''
        else:
            return email

    def get_phone(self, aleph_user):
        z304s = self.get_z304(aleph_user)
        p1 = next((z304['z304-telephone'] for z304 in z304s
                  if self.get_or_empty(z304, 'z304-telephone')), None)
        p2 = next((z304['z304-telephone-2'] for z304 in z304s
                  if self.get_or_empty(z304, 'z304-telephone-2')), None)
        if p1:
            return p1
        elif p2:
            return p2
        else:
            # raise ValueError('No phones found for {}'
            #                .format(self.get_user_name(aleph_user)))
            return ''

    def get_barcode(self, aleph_user):
        return next(z308["z308-key-data"] for z308
                    in aleph_user['z308']
                    if z308['z308-key-type'] == '01')

    def get_user_name(self, aleph_user):
        z06 = next((z308["z308-key-data"] for z308
                    in aleph_user['z308']
                    if z308['z308-key-type'] == '06'), None)
        z03 = next((z308["z308-key-data"] for z308
                    in aleph_user['z308']
                    if z308['z308-key-type'] == '03'), None)
        if not z03 and not z06:
            raise ValueError("no username {}".format(''))
        elif (z03 and z06 and z03 != z06):
            raise ValueError("03 ({}) and 06 ({}) are NOT same"
                             .format(z03, z06))
        elif z03:
            return z03
        elif z06:
            return z06
        elif (z03 and z06 and z03 == z06):
            return z03
        else:
            raise ValueError("SPECIAL CASE: 03: {} 06:{}".format(z03, z06))

    def get_ext_uid(self, aleph_user):
        return next(z308["z308-key-data"] for z308
                    in aleph_user['z308']
                    if z308['z308-key-type'] == '02')

    def get_active(self, aleph_user):
        ac = all(z308['z308-status'] == 'AC' for z308
                 in aleph_user['z308'])
        return ac

    def get_names(self, aleph_user):
        names = aleph_user['z303']['z303-name'].split(',', maxsplit=1)
        return (names[0].strip(), names[1].strip())

    def get_expiration_date(self, aleph_user):
        d_string = self.get_z305(aleph_user)['z305-expiry-date']
        p_date = datetime.strptime(d_string, "%Y%m%d").date()
        return p_date.strftime("%Y-%m-%d")

    def get_elem(self, aleph_user, elem_name):
        class_name = aleph_user[elem_name].__class__.__name__
        if class_name in 'list':
            return iter(aleph_user[elem_name])
        else:
            return iter([aleph_user[elem_name]])

    def get_z304(self, aleph_user):
        return self.get_elem(aleph_user, 'z304')

    def get_z305(self, aleph_user):
        z305s = self.get_elem(aleph_user, 'z305')
        return next(z305 for z305
                    in z305s
                    if ('z305-sub-library' in z305 and
                        z305['z305-sub-library'] != 'ALEPH'))

    def get_or_empty(self, dictionary, key):
        return dictionary[key] if key in dictionary and dictionary[key] else ''

    def get_addresses(self, aleph_user):
        z304s = self.get_z304(aleph_user)
        for z304 in filter(None, z304s):
            line1 = self.get_or_empty(z304, "z304-address-1")
            line2 = self.get_or_empty(z304, "z304-address-2")
            line3 = self.get_or_empty(z304, "z304-address-3")
            temp_country = self.get_or_empty(z304, "z304-address-4")
            # Has country in line 4.
            # Line 3 likely contains a foreign city/state
            if temp_country:
                line2 += line3
                line_to_parse = line3
            # address 3 has NO US state abbr. must conntain country...
            elif line3 and all(' ' + s not in line3 for s in self.states):
                temp_country = line3
                line_to_parse = ''
            # now, this is likely the state-city part of an US address
            elif line3:
                line_to_parse = line3
                temp_country = 'United States of America (the)'
            elif line2:
                line_to_parse = line2
                temp_country = 'United States of America (the)'
            else:
                line_to_parse = ''
                temp_country = 'United States of America (the)'
            addr_type = self.get_or_empty(z304, 'z304-address-type')
            if addr_type == "02":  # Campus
                addr_type_id = "Campus"
                zip_code = ''
            elif addr_type == "01":  # Current
                addr_type_id = "Current"
                zip_code = self.get_zip(z304, self.get_user_name(aleph_user))
            else:
                raise ValueError("addresstype {} for user {}"
                                 .format(addr_type,
                                         self.get_user_name(aleph_user)))

            yield {"countryId": self.get_country_id(temp_country),
                   "addressTypeId": addr_type_id,
                   "addressLine1": line1,
                   "addressLine2": line2,
                   "region": self.get_region(line_to_parse),
                   "city": self.get_city(line_to_parse),
                   "primaryAddress": addr_type == "02",
                   "postalCode": zip_code}

    def get_country_id(self, country):
        try:
            c_id = next(c['ISO3166-1-Alpha-2'].lower() for c
                        in self.country_data
                        if(country) and
                        c['UNTERM English Short'].lower() == country.lower())
            return c_id
        except Exception as a:
            return ''

    def get_region(self, address_line):
        temp_region = ''
        parse = usaddress.tag(address_line)
        return (parse[0]['StateName']
                if 'StateName' in parse[0]
                else temp_region)

    def get_city(self, address_line):
        temp_city = ''
        parse = usaddress.tag(address_line)
        return (parse[0]['PlaceName']
                if 'PlaceName' in parse[0]
                else temp_city)

    def get_zip(self, z304, user_name):
        if 'z304-zip' in z304:
            return z304['z304-zip']
        else:
            raise ValueError('No zip for {}'.format(user_name))
