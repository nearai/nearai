import { zodToJsonSchema } from 'zod-to-json-schema';

import { protocolSchema } from '~/components/threads/messages/aitp/schema';

export async function GET() {
  const schema = zodToJsonSchema(protocolSchema, {
    target: 'jsonSchema2019-09',
    removeAdditionalStrategy: 'strict', // This results in "additionalProperties: true" on all objects, which makes the schema more flexible
  });
  return Response.json(schema);
}
