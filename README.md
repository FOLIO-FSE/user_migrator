# folio_user_migrator
## Users
### Valuable links
[Conversion table for users from Sierra](https://github.com/fontanka16/SierraToFolioConverter/blob/master/conversionTable_users.tsv)   
[FOLIO User import JSON Schema](https://github.com/folio-org/mod-user-import/blob/master/ramls/schemas/userdataimport.json)   
[Explanation of current and future fields in FOLIO](https://docs.google.com/spreadsheets/d/121RpsJNaewhQEKb7k58eNVIhZ7N9oSWowNRJGYjPJ2M/edit?usp=sharing)   
### Examples 
Auto generated JSON Object from the above schema (via https://www.liquid-technologies.com/online-schema-to-json-converter)
```javascript
{
  "username": "ABCDEFGHIJKLMNOPQRSTUVWXYZA",
  "id": "ABCDEFGHIJKLMNOPQRSTUVWXY",
  "externalSystemId": "ABCDEFGHI",
  "barcode": "ABCDEF",
  "active": true,
  "type": "ABCDEFG",
  "patronGroup": "ABCDEFGHIJKLMNO",
  "meta": {},
  "proxyFor": [
    "ABCDEFGHIJ"
  ],
  "personal": {
    "lastName": "ABCDEFGHIJKLMNOPQRSTUVWXYZABC",
    "firstName": "ABCDEFGHIJKLMN",
    "middleName": "ABCDEFGHIJKLMNOPQRSTUVW",
    "email": "ABCDEFGHIJKLMNOP",
    "phone": "ABCDEF",
    "mobilePhone": "ABCD",
    "dateOfBirth": "ABCDEFGHIJKLMNOPQRSTUVWXY",
    "addresses": [
      {
        "id": "ABCDEFGHIJKLMNOPQ",
        "countryId": "ABCDEFGHIJKLMNOPQRSTUVWXYZABC",
        "addressLine1": "ABCDEFG",
        "addressLine2": "ABCDEFGHIJKLMNOPQRSTUVWXYZAB",
        "city": "ABCDEFGHIJKLMNOPQRSTUVWXYZA",
        "region": "ABCDEFGHIJKLMNOPQRSTUVWXYZABC",
        "postalCode": "ABCDEFGHIJKLMNOPQR",
        "addressTypeId": "ABCDEF",
        "primaryAddress": false
      },
      {
        "id": "ABCDEFGH",
        "countryId": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "addressLine1": "ABCDEFGHIJKLMNOPQRSTUVWXYZA",
        "addressLine2": "ABCDEFGHIJKLMNOPQRSTUVWXYZA",
        "city": "ABCDEFGHI",
        "region": "ABCDEFG",
        "postalCode": "ABCDEFGHIJKLM",
        "addressTypeId": "ABCDEFGHIJKLMNOPQRSTUVWXY",
        "primaryAddress": true
      }
    ],
    "preferredContactTypeId": "ABCDEFGHIJKLMNOPQRSTUVW"
  },
  "enrollmentDate": "ABCDEFGHIJKLMN",
  "expirationDate": "ABCDEFGHIJKLMNOPQ",
  "createdDate": "ABCDE",
  "updatedDate": "ABCDEF",
  "metadata": {
    "createdDate": "ABCDEFGHIJKLMNOPQRSTUVWXYZA",
    "createdByUserId": "eAE3cFFc-BE2F-FDee-dbBC-Cb1bBD2ff70c",
    "createdByUsername": "ABCD",
    "updatedDate": "ABCDEFGHIJKLMNOPQRSTUVWXYZAB",
    "updatedByUserId": "1CABD4Bd-BCCE-DBeE-EEDB-46B6FfCDaEE9",
    "updatedByUsername": "ABCDEFGHIJKLMNOPQRSTUVWXY"
  }
}
```
[A Sierra User in JSON Format](https://github.com/fontanka16/SierraToFolioConverter/blob/master/exampleRecords/example_user.json)