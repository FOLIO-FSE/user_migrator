import json
import usaddress
from datetime import datetime
import uuid
import requests
import csv
import io


class Aleph:

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
        return json.load(source_file)["p-file-20"]["patron-record"]

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
                             "phone": aleph_user["z304"]["z304-telephone"],
                             "email": aleph_user["z304"]["z304-email-address"],
                             "addresses": [self.get_addresses(aleph_user)]},
                "expirationDate": self.get_expiration_date(aleph_user)}

    def get_group(self, aleph_user):
        a_group = self.get_z305(aleph_user)['z305-bor-status']
        return next(g['Folio Code'] for g
                    in self.groupsmap
                    if g['ALEPH code'] == a_group)

    def get_barcode(self, aleph_user):
        return next(z308["z308-key-data"] for z308
                    in aleph_user['z308']
                    if z308['z308-key-type'] == '01')

    def get_user_name(self, aleph_user):
        return next(z308["z308-key-data"] for z308
                    in aleph_user['z308']
                    if z308['z308-key-type'] == '06')

    def get_ext_uid(self, aleph_user):
        return next(z308["z308-key-data"] for z308
                    in aleph_user['z308']
                    if z308['z308-key-type'] == '02')

    def get_active(self, aleph_user):
        # ac = all(z308['z308-status'] == 'AC' for z308
        #         in aleph_user['z308'])
        # print(ac)
        # return ac
        return True

    def get_names(self, aleph_user):
        names = aleph_user['z303']['z303-name'].split(',', maxsplit=1)
        return (names[0].strip(), names[1].strip())

    def get_expiration_date(self, aleph_user):
        d_string = self.get_z305(aleph_user)['z305-expiry-date']
        p_date = datetime.strptime(d_string, "%Y%m%d").date()
        return p_date.strftime("%Y-%m-%d")

    def get_z305(self, aleph_user):
        return next(z305 for z305
                    in aleph_user['z305']
                    if z305['z305-sub-library'] == 'HAM50')

    def get_addresses(self, aleph_user):
        z304 = aleph_user['z304']
        line1 = z304["z304-address-1"] if "z304-address-1" in z304 else ''
        line2 = z304["z304-address-2"] if "z304-address-2" in z304 else ''
        temp_country = (z304["z304-address-4"] if 'z304-address-4' in z304
                        else '')
        # Has country in line 4. Line 3 likely contains a foreign city/state
        if temp_country:
            line2 += z304["z304-address-3"]
            line_to_parse = z304["z304-address-3"]
        # address 3 has NO US state abbr. must conntain country...
        elif 'z304-address-3' in z304 and all(' ' + state
                                              not in z304['z304-address-3']
                                              for state
                                              in self.states):
            temp_country = z304["z304-address-3"]
            line_to_parse = ''
        # now, this is likely the state-city part of an US address
        elif 'z304-address-3' in z304:
            line_to_parse = z304['z304-address-3']
            temp_country = 'United States of America (the)'
        elif 'z304-address-2' in z304:
            line_to_parse = z304['z304-address-2']
            temp_country = 'United States of America (the)'
        else:
            line_to_parse = ''
            temp_country = 'United States of America (the)'
        return {"countryId": self.get_country_id(temp_country),
                "addressTypeId": "Home",
                "addressLine1": line1,
                "addressLine2": line2,
                "region": self.get_region(line_to_parse),
                "city": self.get_city(line_to_parse),
                "primaryAddress": True,
                "postalCode": self.get_zip(aleph_user)}

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

    def get_zip(self, aleph_user):
        return aleph_user['z304']['z304-zip']
