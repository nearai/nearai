import { z } from 'zod';

const requestChoiceOptionSchema = z.object({
  name: z.string(),
  shortVariantName: z.string().optional(),
  image_url: z.string().url().optional(),
  description: z.string().optional(),
  price_usd: z.number().optional(),
  reviewsCount: z
    .number()
    .int()
    .refine((value) => (value ? Math.ceil(value) : value))
    .optional(),
  fiveStarRating: z
    .number()
    .min(0)
    .max(5)
    .refine((value) => (value ? Math.min(Math.max(value, 0), 5) : value))
    .optional(),
  url: z.string().url().optional(),
});

export const requestChoiceSchema = z.object({
  request_choice: z.object({
    title: z.string().optional(),
    description: z.string().optional(),
    type: z
      .enum(['products', 'checkbox', 'radio', 'confirmation'])
      .default('radio')
      .optional(),
    options: requestChoiceOptionSchema
      .extend({
        variants: requestChoiceOptionSchema.array().optional(),
      })
      .array()
      .default([])
      .optional(),
  }),
});

export const requestDataSchema = z.object({
  request_data: z.object({
    schema: z
      .enum([
        'https://docs.near.ai/v1/agent_protocol/request_data/shipping.schema.json',
      ])
      .optional(),
    fields: z
      .object({
        name: z.string().optional(),
        label: z.string(),
        description: z.string().optional(),
        defaultValue: z.string().optional(),
        type: z.enum(['text', 'textarea', 'number', 'email']).default('text'),
        required: z.boolean().default(false),
      })
      .array()
      .optional(),
  }),
});

/*
  The payment schema is unknown at this time...

  export const requestPaymentSchema = z.object({
    request_payment: z.object({
      version: z.string(),
    }),
  });
*/

export const protocolSchema = requestChoiceSchema.or(requestDataSchema);
