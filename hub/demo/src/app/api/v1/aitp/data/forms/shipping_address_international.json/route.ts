import { type z } from 'zod';

import { type requestDataFormSchema } from '~/components/threads/messages/aitp/schema/data';

// See "Generic Formats": https://www.uxmatters.com/mt/archives/2008/06/international-address-fields-in-web-forms.php

export async function GET() {
  const form: z.infer<typeof requestDataFormSchema> = {
    fields: [
      {
        id: 'email_address',
        label: 'Email Address',
        type: 'email',
        required: true,
        description:
          'Order and tracking information will be sent to this email',
        autocomplete: 'email',
      },
      {
        id: 'full_name',
        label: 'Full Name',
        type: 'text',
        required: true,
        autocomplete: 'name',
      },
      {
        id: 'address_line_1',
        label: 'Address Line 1',
        type: 'text',
        description: 'Street address, P.O. box, company name, etc',
        autocomplete: 'address-line1',
        required: true,
      },
      {
        id: 'address_line_2',
        label: 'Address Line 2',
        type: 'text',
        description: 'Apartment, suite, unit, building, floor, etc',
        autocomplete: 'address-line2',
        required: false,
      },
      {
        id: 'city',
        label: 'City',
        type: 'text',
        autocomplete: 'address-level2',
        required: true,
      },
      {
        id: 'province',
        label: 'Province / State',
        type: 'text',
        autocomplete: 'address-level1',
        required: true,
      },
      {
        id: 'postal_code',
        label: 'Postal Code / ZIP',
        type: 'text',
        autocomplete: 'postal-code',
        required: true,
      },
      {
        id: 'country',
        label: 'Country',
        type: 'combobox',
        autocomplete: 'country-name',
        options: [
          'Afghanistan',
          'Aland Islands',
          'Albania',
          'Algeria',
          'American Samoa',
          'Andorra',
          'Angola',
          'Anguilla',
          'Antarctica',
          'Antigua and Barbuda',
          'Argentina',
          'Armenia',
          'Aruba',
          'Australia',
          'Austria',
          'Azerbaijan',
          'Bahamas',
          'Bahrain',
          'Bangladesh',
          'Barbados',
          'Belarus',
          'Belgium',
          'Belize',
          'Benin',
          'Bermuda',
          'Bhutan',
          'Bolivia (Plurinational State of)',
          'Bosnia and Herzegovina',
          'Botswana',
          'Bouvet Island',
          'Brazil',
          'British Indian Ocean Territory',
          'Brunei Darussalam',
          'Bulgaria',
          'Burkina Faso',
          'Burundi',
          'Cabo Verde',
          'Cambodia',
          'Cameroon',
          'Canada',
          'Caribbean Netherlands',
          'Cayman Islands',
          'Central African Republic',
          'Chad',
          'Chile',
          'China',
          'Christmas Island',
          'Cocos (Keeling) Islands',
          'Colombia',
          'Comoros',
          'Congo',
          'Congo, Democratic Republic of the',
          'Cook Islands',
          'Costa Rica',
          'Croatia',
          'Cuba',
          'Curaçao',
          'Cyprus',
          'Czech Republic',
          "Côte d'Ivoire",
          'Denmark',
          'Djibouti',
          'Dominica',
          'Dominican Republic',
          'Ecuador',
          'Egypt',
          'El Salvador',
          'Equatorial Guinea',
          'Eritrea',
          'Estonia',
          'Eswatini (Swaziland)',
          'Ethiopia',
          'Falkland Islands (Malvinas)',
          'Faroe Islands',
          'Fiji',
          'Finland',
          'France',
          'French Guiana',
          'French Polynesia',
          'French Southern Territories',
          'Gabon',
          'Gambia',
          'Georgia',
          'Germany',
          'Ghana',
          'Gibraltar',
          'Greece',
          'Greenland',
          'Grenada',
          'Guadeloupe',
          'Guam',
          'Guatemala',
          'Guernsey',
          'Guinea',
          'Guinea-Bissau',
          'Guyana',
          'Haiti',
          'Heard Island and Mcdonald Islands',
          'Honduras',
          'Hong Kong',
          'Hungary',
          'Iceland',
          'India',
          'Indonesia',
          'Iran',
          'Iraq',
          'Ireland',
          'Isle of Man',
          'Israel',
          'Italy',
          'Jamaica',
          'Japan',
          'Jersey',
          'Jordan',
          'Kazakhstan',
          'Kenya',
          'Kiribati',
          'Korea, North',
          'Korea, South',
          'Kosovo',
          'Kuwait',
          'Kyrgyzstan',
          "Lao People's Democratic Republic",
          'Latvia',
          'Lebanon',
          'Lesotho',
          'Liberia',
          'Libya',
          'Liechtenstein',
          'Lithuania',
          'Luxembourg',
          'Macao',
          'Macedonia North',
          'Madagascar',
          'Malawi',
          'Malaysia',
          'Maldives',
          'Mali',
          'Malta',
          'Marshall Islands',
          'Martinique',
          'Mauritania',
          'Mauritius',
          'Mayotte',
          'Mexico',
          'Micronesia',
          'Moldova',
          'Monaco',
          'Mongolia',
          'Montenegro',
          'Montserrat',
          'Morocco',
          'Mozambique',
          'Myanmar (Burma)',
          'Namibia',
          'Nauru',
          'Nepal',
          'Netherlands',
          'Netherlands Antilles',
          'New Caledonia',
          'New Zealand',
          'Nicaragua',
          'Niger',
          'Nigeria',
          'Niue',
          'Norfolk Island',
          'Northern Mariana Islands',
          'Norway',
          'Oman',
          'Pakistan',
          'Palau',
          'Palestine',
          'Panama',
          'Papua New Guinea',
          'Paraguay',
          'Peru',
          'Philippines',
          'Pitcairn Islands',
          'Poland',
          'Portugal',
          'Puerto Rico',
          'Qatar',
          'Reunion',
          'Romania',
          'Russian Federation',
          'Rwanda',
          'Saint Barthelemy',
          'Saint Helena',
          'Saint Kitts and Nevis',
          'Saint Lucia',
          'Saint Martin',
          'Saint Pierre and Miquelon',
          'Saint Vincent and the Grenadines',
          'Samoa',
          'San Marino',
          'Sao Tome and Principe',
          'Saudi Arabia',
          'Senegal',
          'Serbia',
          'Serbia and Montenegro',
          'Seychelles',
          'Sierra Leone',
          'Singapore',
          'Sint Maarten',
          'Slovakia',
          'Slovenia',
          'Solomon Islands',
          'Somalia',
          'South Africa',
          'South Georgia and the South Sandwich Islands',
          'South Sudan',
          'Spain',
          'Sri Lanka',
          'Sudan',
          'Suriname',
          'Svalbard and Jan Mayen',
          'Sweden',
          'Switzerland',
          'Syria',
          'Taiwan',
          'Tajikistan',
          'Tanzania',
          'Thailand',
          'Timor-Leste',
          'Togo',
          'Tokelau',
          'Tonga',
          'Trinidad and Tobago',
          'Tunisia',
          'Turkey (Türkiye)',
          'Turkmenistan',
          'Turks and Caicos Islands',
          'Tuvalu',
          'U.S. Outlying Islands',
          'Uganda',
          'Ukraine',
          'United Arab Emirates',
          'United Kingdom',
          'United States',
          'Uruguay',
          'Uzbekistan',
          'Vanuatu',
          'Vatican City Holy See',
          'Venezuela',
          'Vietnam',
          'Virgin Islands, British',
          'Virgin Islands, U.S',
          'Wallis and Futuna',
          'Western Sahara',
          'Yemen',
          'Zambia',
          'Zimbabwe',
        ],
        required: true,
      },
    ],
  };

  return Response.json(form);
}
