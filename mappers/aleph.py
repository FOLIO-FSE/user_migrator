import json
import uuid
import requests
from jsonschema import validate


class Aleph:

    def __init__(self, config):
        print(config)

    def do_map(self, aleph_user):
        return {'id': str(uuid.uuid4()),
                'patronGroup': self.get_group(aleph_user),
                'barcode': self.get_barcode(aleph_user),
                'username': self.get_user_name(aleph_user),
                'externalSystemId': self.get_ext_uid(aleph_user),
                'active': self.get_active(aleph_user),
                'personal': {'preferredContactTypeId': 'mail',
                             'lastName': self.get_names(aleph_user)[0],
                             'firstName': self.get_names(aleph_user)[1],
                             'phone': aleph_user['z304']['z304-telephone'],
                             'addresses': self.get_addresses(aleph_user)},
                'expirationDate': self.get_expiration_date(aleph_user)}

    def get_group(self, aleph_user):
        return ''

    def get_barcode(self, aleph_user):
        return ''

    def get_user_name(self, aleph_user):
        return ''

    def get_ext_uid(self, aleph_user):
        return ''

    def get_active(self, aleph_user):
        return ''

    def get_names(self, aleph_user):
        return {'', ''}

    def get_addresses(self, aleph_user):
        return {'countryId': self.get_country_id(aleph_user),
                'addressTypeId': '',
                'addressLine1': aleph_user['z304']['z304-address-1'],
                'addressLine2': aleph_user['z304']['z304-address-2'],
                'region': self.get_region(aleph_user),
                'city': self.get_city(aleph_user),
                'primaryAddress': True,
                'postalCode': self.get_zip(aleph_user)}

    def get_country_id(self, aleph_user):
        return ''

    def get_region(self, aleph_user):
        return ''

    def get_city(self, aleph_user):
        return ''

    def get_zip(self, aleph_user):
        return ''

