import { z } from 'zod';
import { baseSchema } from './base';

export const quoteSchema = baseSchema
    .extend({
        quote: z.object({
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
            .passthrough(),
    });
