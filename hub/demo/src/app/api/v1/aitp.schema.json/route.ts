import { zodToJsonSchema } from 'zod-to-json-schema';

import { protocolSchema } from '~/components/threads/messages/aitp/schema';

export async function GET() {
  const schema = zodToJsonSchema(protocolSchema, {
    target: 'jsonSchema2019-09',
  });
  return Response.json(schema);
}
