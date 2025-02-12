import { z } from 'zod';

import { baseSchema } from './base';

export const requestDataFormFieldSchema = z
  .object({
    id: z.string(),
    label: z.string().optional(),
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
    fields: requestDataFormFieldSchema.array().min(1).optional(),
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
      id: z.string(),
      title: z.string().optional(),
      description: z.string(),
      fillButtonLabel: z.string().default('Fill out form'),
      forms: requestDataFormSchema.array().min(1),
    })
    .passthrough(),
});

export const dataSchema = baseSchema.extend({
  data: z
    .object({
      request_data_id: z.string().optional(),
      fields: z
        .object({
          id: z.string(),
          label: z.string().optional(),
          value: z.string().optional(),
        })
        .array()
        .min(1),
    })
    .passthrough(),
});
