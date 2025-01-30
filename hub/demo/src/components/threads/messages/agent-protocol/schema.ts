import { z } from 'zod';

export const CURRENT_AGENT_PROTOCOL_SCHEMA =
  'https://app.near.ai/api/v1/agent_protocol.schema.json';

const requestChoiceOptionSchema = z.object({
  name: z.string(),
  short_variant_name: z.string().optional(),
  image_url: z.string().url().optional(),
  description: z.string().optional(),
  price_usd: z.number().optional(),
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
});

export const requestChoiceSchema = z.object({
  request_choice: z.object({
    title: z.string().optional(),
    description: z.string().optional(),
    type: z
      .enum(['products', 'checkbox', 'radio', 'confirmation'])
      .default('radio'),
    options: requestChoiceOptionSchema
      .extend({
        variants: requestChoiceOptionSchema.array().optional(),
      })
      .array()
      .default([]),
  }),
});

export const requestDataFormFieldSchema = z.object({
  name: z.string().optional(),
  label: z.string(),
  description: z.string().optional(),
  default_value: z.string().optional(),
  type: z.enum(['text', 'textarea', 'number', 'email']).default('text'),
  required: z.boolean().default(false),
  autocomplete: z.string().optional(), // https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/autocomplete
});

export const requestDataFormSchema = z.object({
  title: z.string().optional(),
  description: z.string().optional(),
  fields: requestDataFormFieldSchema.array().optional(),
  json_url: z
    .enum([
      'https://app.near.ai/api/v1/agent_protocol/request_data/forms/shipping_address_international.json',
      'https://app.near.ai/api/v1/agent_protocol/request_data/forms/shipping_address_us.json',
    ])
    .or(z.string().url())
    .optional(),
});

export const requestDataSchema = z.object({
  request_data: z.object({
    title: z.string().optional(),
    description: z.string(),
    fillButtonLabel: z.string().default('Fill out form'),
    forms: requestDataFormSchema.array(),
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
