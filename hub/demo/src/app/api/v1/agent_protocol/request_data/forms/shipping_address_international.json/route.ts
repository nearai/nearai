import { type z } from 'zod';

import { type requestDataFormSchema } from '~/components/threads/messages/agent-protocol/schema';

// See "Generic Formats": https://www.uxmatters.com/mt/archives/2008/06/international-address-fields-in-web-forms.php

export async function GET() {
  const form: z.infer<typeof requestDataFormSchema> = {
    title: 'Shipping Info',
    description:
      'Please provide the address where your order should be delivered.',
    fields: [
      {
        label: 'Email Address',
        type: 'email',
        required: true,
        description:
          'Order and tracking information will be sent to this email',
        autocomplete: 'email',
      },
      {
        label: 'Full Name',
        type: 'text',
        required: true,
        autocomplete: 'name',
      },
      {
        label: 'Address Line 1',
        type: 'text',
        description: 'Street address, P.O. box, company name, etc',
        autocomplete: 'address-line1',
        required: true,
      },
      {
        label: 'Address Line 2',
        type: 'text',
        description: 'Apartment, suite, unit, building, floor, etc',
        autocomplete: 'address-line2',
        required: false,
      },
      {
        label: 'City',
        type: 'text',
        autocomplete: 'address-level2',
        required: true,
      },
      {
        label: 'Province / State',
        type: 'text',
        autocomplete: 'address-level1',
        required: true,
      },
      {
        label: 'Postal Code / ZIP',
        type: 'text',
        autocomplete: 'postal-code',
        required: true,
      },
      {
        label: 'Country',
        type: 'text',
        autocomplete: 'country-name',
        required: true,
      },
    ],
  };

  return Response.json(form);
}
