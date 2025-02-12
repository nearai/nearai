import { z } from 'zod';

export const CURRENT_AGENT_PROTOCOL_SCHEMA =
  'https://app.near.ai/api/v1/aitp.schema.json';

export const baseSchema = z.object({
  $schema: z.enum([CURRENT_AGENT_PROTOCOL_SCHEMA]).or(z.string().url()),
});
