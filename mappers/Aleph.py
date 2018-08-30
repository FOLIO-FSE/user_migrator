import uuid


class Aleph:

    def __init__(self, config):
        self.groupsmap = config["groupsmap"]

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
                             "addresses": self.get_addresses(aleph_user)},
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
        return all(z308['z308-status'] == 'AC' for z308
                   in aleph_user['z308'])

    def get_names(self, aleph_user):
        names = aleph_user['z303']['z303-name'].split(',', maxsplit=1)
        return (names[0].strip(), names[1].strip())

    def get_expiration_date(self, aleph_user):
        return self.get_z305(aleph_user)['z305-expiry-date']

    def get_z305(self, aleph_user):
        return next(z305 for z305
                    in aleph_user['z305']
                    if z305['z305-sub-library'] == 'HAM50')

    def get_addresses(self, aleph_user):
        z304 = aleph_user['z304']
        line1 = z304["z304-address-1"] if "z304-address-1" in z304 else ''
        line2 = z304["z304-address-2"] if "z304-address-2" in z304 else ''

        return {"countryId": self.get_country_id(aleph_user),
                "addressTypeId": "",
                "addressLine1": line1,
                "addressLine2": line2,
                "region": self.get_region(aleph_user),
                "city": self.get_city(aleph_user),
                "primaryAddress": True,
                "postalCode": self.get_zip(aleph_user)}

    def get_country_id(self, aleph_user):
        return ""

    def get_region(self, aleph_user):
        return ""

    def get_city(self, aleph_user):
        return ""

    def get_zip(self, aleph_user):
        return ""
