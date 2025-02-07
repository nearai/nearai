// AITP = Agent Interaction & Transaction Protocol

import { z } from 'zod';

export const CURRENT_AGENT_PROTOCOL_SCHEMA =
  'https://app.near.ai/api/v1/aitp.schema.json';

const baseSchema = z.object({
  $schema: z.enum([CURRENT_AGENT_PROTOCOL_SCHEMA]).or(z.string().url()),
});

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
    name: z.string(),
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
        .default([]),
    })
    .passthrough(),
});

export const requestDataFormFieldSchema = z
  .object({
    label: z.string(),
    description: z.string().optional(),
    default_value: z.string().optional(),
    type: z
      .enum([
        'text',
        'number',
        'email',
        'textarea',
        'select',
        'combobox',
        'tel',
      ])
      .default('text'),
    options: z.string().array().optional(),
    required: z.boolean().default(false),
    autocomplete: z.string().optional(), // https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/autocomplete
  })
  .passthrough();

export const requestDataFormSchema = z
  .object({
    title: z.string().optional(),
    description: z.string().optional(),
    fields: requestDataFormFieldSchema.array().optional(),
    json_url: z
      .enum([
        'https://app.near.ai/api/v1/aitp/request_data/forms/shipping_address_international.json',
        'https://app.near.ai/api/v1/aitp/request_data/forms/shipping_address_us.json',
      ])
      .or(z.string().url())
      .optional(),
  })
  .passthrough();

export const requestDataSchema = baseSchema.extend({
  request_data: z
    .object({
      title: z.string().optional(),
      description: z.string(),
      fillButtonLabel: z.string().default('Fill out form'),
      forms: requestDataFormSchema.array(),
    })
    .passthrough(),
});

/*
The payment schema is unknown at this time...

export const requestPaymentSchema = z.object({
  request_payment: z.object({
    version: z.string(),
  }),
});
*/

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
  requestDecisionSchema.passthrough(),
  requestDataSchema.passthrough(),
]);

const aitpSchemaWithoutPassthrough = z.union([
  requestDecisionSchema,
  requestDataSchema,
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
