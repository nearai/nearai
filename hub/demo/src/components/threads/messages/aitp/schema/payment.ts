import { z } from 'zod';

import { baseSchema } from './base';

export const CURRENT_AITP_PAYMENT_SCHEMA_URL =
  'https://aitp.dev/v1/payment/schema.json';

export const nestedQuoteSchema = z
  .object({
    type: z.enum(['Quote']),
    quote_id: z.string(),
    payee_id: z.string(),
    payment_plans: z
      .object({
        plan_id: z.string(),
        plan_type: z.enum(['one-time']),
        amount: z.number(),
        currency: z.enum(['USD']),
      })
      .passthrough()
      .array(),
    valid_until: z.string().datetime(),
  })
  .passthrough();

export const quoteSchema = baseSchema.extend({
  quote: nestedQuoteSchema,
});

export const paymentConfirmationSchema = baseSchema.extend({
  payment_confirmation: z
    .object({
      transaction_id: z.string(),
      quote_id: z.string(),
      result: z.enum(['success', 'failure']),
      message: z.string().optional(),
      timestamp: z.string().datetime(),
    })
    .passthrough(),
});
