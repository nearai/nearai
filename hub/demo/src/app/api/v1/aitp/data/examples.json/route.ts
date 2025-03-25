import { type z } from 'zod';

import {
  CURRENT_AITP_DATA_SCHEMA_URL,
  type dataSchema,
} from '@/components/threads/messages/aitp/schema/data';
import {
  mockRequestDataFavorites,
  mockRequestDataShippingAddressInternational,
} from '@/trpc/utils/mock-aitp';

export async function GET() {
  const data: z.infer<typeof dataSchema> = {
    $schema: CURRENT_AITP_DATA_SCHEMA_URL,
    data: {
      request_data_id: crypto.randomUUID(),
      fields: [
        {
          id: 'favorite_color',
          label: 'Favorite Color',
          value: 'Blue',
        },
        {
          id: 'favorite_number',
          label: 'Favorite Number',
          value: '7',
        },
      ],
    },
  };

  return Response.json({
    data,
    request_data: mockRequestDataFavorites,
    request_data_json_url: mockRequestDataShippingAddressInternational,
  });
}
