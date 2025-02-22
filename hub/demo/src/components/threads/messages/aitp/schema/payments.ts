import { z } from 'zod';

import { baseSchema } from './base';

export const CURRENT_AITP_PAYMENTS_SCHEMA_URL =
  'https://aitp.dev/v1/payments/schema.json';

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

export const paymentAuthorizationSchema = baseSchema.extend({
  payment_authorization: z
    .object({
      quote_id: z.string(),
      result: z.enum(['success', 'failure']),
      message: z.string().optional(),
      timestamp: z.string().datetime(),
      details: z
        .object({
          network: z.enum(['NEAR']),
          token_type: z.enum(['USDC']),
          amount: z.number(),
          account_id: z.string(),
          transaction_id: z.string(),
        })
        .array(),
    })
    .passthrough(),
});

export const paymentResultSchema = baseSchema.extend({
  payment_result: z
    .object({
      quote_id: z.string(),
      result: z.enum(['success', 'failure']),
      timestamp: z.string().datetime(),
      message: z.string().optional(),
      details: z
        .object({
          label: z.string(),
          url: z.string().url().optional(),
          value: z.string().or(z.number()),
        })
        .array(),
    })
    .passthrough(),
});
