import { z } from 'zod';

import { baseSchema } from './base';

export const CURRENT_AITP_DATA_SCHEMA_URL =
  'https://aitp.dev/v1/data/schema.json';

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
    options: z
      .union([
        z.string().array(),
        z.object({ label: z.string(), value: z.string() }).array(),
      ])
      .optional(),
    required: z.boolean().default(false),
    autocomplete: z.string().optional(), // https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/autocomplete
  })
  .passthrough();

export const requestDataFormSchema = z
  .object({
    fields: requestDataFormFieldSchema.array().min(1).optional(),
    json_url: z.string().url().optional(),
  })
  .passthrough();

export const requestDataSchema = baseSchema
  .extend({
    request_data: z
      .object({
        id: z.string(),
        title: z.string().optional(),
        description: z.string(),
        fillButtonLabel: z.string().default('Fill out form'),
        form: requestDataFormSchema,
      })
      .passthrough(),
  })
  .passthrough();

export const dataSchema = baseSchema
  .extend({
    data: z
      .object({
        request_data_id: z.string().optional(),
        fields: z
          .object({
            id: z.string(),
            label: z.string().optional(),
            value: z.string().optional(),
          })
          .passthrough()
          .array()
          .min(1),
      })
      .passthrough(),
  })
  .passthrough();
