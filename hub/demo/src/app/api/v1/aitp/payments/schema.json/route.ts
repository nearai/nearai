import * as migrate from 'json-schema-migrate';
import { z } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';

import {
  paymentAuthorizationSchema,
  paymentResultSchema,
  quoteSchema,
} from '@/components/threads/messages/aitp/schema/payments';

export async function GET() {
  const schema = zodToJsonSchema(
    z.union([paymentAuthorizationSchema, paymentResultSchema, quoteSchema]),
    {
      target: 'jsonSchema2019-09',
    },
  );

  migrate.draft2020(schema);

  const { $schema, ...rest } = schema;

  return Response.json({
    $schema: 'https://json-schema.org/draft/2020-12/schema',
    ...rest,
  });
}
