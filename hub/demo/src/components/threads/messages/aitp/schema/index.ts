// AITP = Agent Interaction & Transaction Protocol

import { z } from 'zod';

import { dataSchema, requestDataSchema } from './data';
import { decisionSchema, requestDecisionSchema } from './decision';

/*
  NOTE: The following duplication of aitpSchema and aitpSchemaWithoutPassthrough is 
  a necessary evil to get desired behavior (passthrough unknown properties) while 
  having strong types to work with after a successful schema parse. Zod's computed 
  types incorrectly result in "unknown" when combining z.union() with objects that 
  use passthrough().

  When adding a new schema, be sure to add it to both aitpSchema and 
  aitpSchemaWithoutPassthrough.
*/

export const aitpSchema = z.union([
  dataSchema.passthrough(),
  decisionSchema.passthrough(),
  requestDataSchema.passthrough(),
  requestDecisionSchema.passthrough(),
]);

const aitpSchemaWithoutPassthrough = z.union([
  dataSchema,
  decisionSchema,
  requestDataSchema,
  requestDecisionSchema,
]);

type AitpSchema = z.infer<typeof aitpSchemaWithoutPassthrough>;

export function parseJsonWithAitpSchema(json: Record<string, unknown>) {
  const result = aitpSchema.safeParse(json);
  const data = result.data ? (result.data as AitpSchema) : null;
  return {
    error: result.error,
    ...data,
  };
}
