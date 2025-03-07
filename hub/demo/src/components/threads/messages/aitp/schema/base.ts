import { z } from 'zod';

export const baseSchema = z.object({
  $schema: z.string().url(),
});
