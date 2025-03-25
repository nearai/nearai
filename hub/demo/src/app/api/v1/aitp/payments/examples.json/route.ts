import { type z } from 'zod';

import {
  CURRENT_AITP_PAYMENTS_SCHEMA_URL,
  type paymentAuthorizationSchema,
  type paymentResultSchema,
  type quoteSchema,
} from '@/components/threads/messages/aitp/schema/payments';

export async function GET() {
  const paymentAuthorization: z.infer<typeof paymentAuthorizationSchema> = {
    $schema: CURRENT_AITP_PAYMENTS_SCHEMA_URL,
    payment_authorization: {
      details: [
        {
          account_id: 'customer.near',
          amount: 2.5,
          network: 'NEAR',
          token_type: 'USDC',
          transaction_id: '7vjj6uqQeyYciPNhA9jiRvfH98LVeJ7C8df4Q9rA3SfN',
        },
      ],
      quote_id: 'quote_123',
      result: 'success',
      timestamp: '2050-01-01T00:00:00Z',
    },
  };

  const paymentResult: z.infer<typeof paymentResultSchema> = {
    $schema: CURRENT_AITP_PAYMENTS_SCHEMA_URL,
    payment_result: {
      details: [
        {
          label: 'Some Number',
          value: 123,
          url: 'https://near.ai',
        },
        {
          label: 'Color',
          value: 'Red',
        },
      ],
      message: 'Your red socks are on their way!',
      quote_id: 'quote_123',
      result: 'success',
      timestamp: '2050-01-01T00:00:00Z',
    },
  };

  const quote: z.infer<typeof quoteSchema> = {
    $schema: CURRENT_AITP_PAYMENTS_SCHEMA_URL,
    quote: {
      payee_id: 'merchant.near',
      quote_id: 'quote_123',
      payment_plans: [
        {
          amount: 2.5,
          currency: 'USD',
          plan_id: 'plan_123',
          plan_type: 'one-time',
        },
      ],
      type: 'Quote',
      valid_until: '2050-01-01T00:00:00Z',
    },
  };

  return Response.json({
    paymentAuthorization,
    paymentResult,
    quote,
  });
}
