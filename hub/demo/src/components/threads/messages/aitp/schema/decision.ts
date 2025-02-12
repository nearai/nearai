import { z } from 'zod';

import { baseSchema } from './base';

export const quoteSchema = z
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

const requestDecisionOptionSchema = z
  .object({
    id: z.string(),
    name: z.string().optional(),
    short_variant_name: z.string().optional(),
    image_url: z.string().url().optional(),
    description: z.string().optional(),
    quote: quoteSchema.optional(),
    reviews_count: z
      .number()
      .int()
      .refine((value) => (value ? Math.ceil(value) : value))
      .optional(),
    five_star_rating: z
      .number()
      .min(0)
      .max(5)
      .refine((value) => (value ? Math.min(Math.max(value, 0), 5) : value))
      .optional(),
    url: z.string().url().optional(),
  })
  .passthrough();

export const requestDecisionSchema = baseSchema.extend({
  request_decision: z
    .object({
      id: z.string(),
      title: z.string().optional(),
      description: z.string().optional(),
      type: z
        .enum(['products', 'checkbox', 'radio', 'confirmation'])
        .default('radio'),
      options: requestDecisionOptionSchema
        .extend({
          variants: requestDecisionOptionSchema.array().optional(),
        })
        .array()
        .min(1),
    })
    .passthrough(),
});

export const decisionSchema = baseSchema.extend({
  decision: z
    .object({
      request_decision_id: z.string().optional(),
      options: z
        .object({
          id: z.string(),
          name: z.string().optional(),
          quantity: z.number().optional(),
        })
        .array()
        .min(1),
    })
    .passthrough(),
});
