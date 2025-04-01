// AITP = Agent Interaction & Transaction Protocol

import { z } from 'zod';

import {
  CURRENT_AITP_DATA_SCHEMA_URL,
  dataSchema,
  requestDataSchema,
} from './data';
import {
  CURRENT_AITP_DECISIONS_SCHEMA_URL,
  decisionSchema,
  requestDecisionSchema,
} from './decisions';
import {
  CURRENT_AITP_PAYMENTS_SCHEMA_URL,
  paymentAuthorizationSchema,
  paymentResultSchema,
  quoteSchema,
} from './payments';

export const AITP_CLIENT_ID = 'app.near.ai';

export const AITP_CAPABILITIES = [
  CURRENT_AITP_DATA_SCHEMA_URL,
  CURRENT_AITP_DECISIONS_SCHEMA_URL,
  CURRENT_AITP_PAYMENTS_SCHEMA_URL,
] as const;

/*
  NOTE: The following duplication of aitpSchema and aitpSchemaWithoutPassthrough is 
  a necessary evil to get desired behavior (passthrough unknown properties) while 
  having strong types to work with after a successful schema parse. Zod's computed 
  types incorrectly result in "unknown" when combining z.union() with objects that 
  use passthrough().

  When adding a new schema, be sure to add it to both aitpSchema and 
  aitpSchemaWithoutPassthrough.
*/

const aitpSchema = z.union([
  dataSchema,
  decisionSchema,
  paymentAuthorizationSchema,
  paymentResultSchema,
  quoteSchema,
  requestDataSchema,
  requestDecisionSchema,
]);

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const aitpSchemaWithoutPassthrough = z.union([
  dataSchema.strip(),
  decisionSchema.strip(),
  paymentAuthorizationSchema.strip(),
  paymentResultSchema.strip(),
  quoteSchema.strip(),
  requestDataSchema.strip(),
  requestDecisionSchema.strip(),
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
