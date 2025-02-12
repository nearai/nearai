import { zodToJsonSchema } from 'zod-to-json-schema';

import { aitpSchema } from '~/components/threads/messages/aitp/schema';

export async function GET() {
  const schema = zodToJsonSchema(aitpSchema, {
    target: 'jsonSchema2019-09',
  });

  return Response.json(schema);
}
