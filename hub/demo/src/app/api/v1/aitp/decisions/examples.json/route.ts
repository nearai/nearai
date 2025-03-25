import { type z } from 'zod';

import {
  CURRENT_AITP_DECISIONS_SCHEMA_URL,
  type decisionSchema,
} from '@/components/threads/messages/aitp/schema/decisions';
import {
  mockRequestDecisionCheckbox,
  mockRequestDecisionConfirmation,
  mockRequestDecisionProducts,
  mockRequestDecisionRadio,
} from '@/trpc/utils/mock-aitp';

export async function GET() {
  const decision: z.infer<typeof decisionSchema> = {
    $schema: CURRENT_AITP_DECISIONS_SCHEMA_URL,
    decision: {
      request_decision_id: crypto.randomUUID(),
      options: [
        {
          id: 'red',
          name: 'Red',
        },
        {
          id: 'blue',
          name: 'Blue',
        },
      ],
    },
  };

  const decision_products: z.infer<typeof decisionSchema> = {
    $schema: CURRENT_AITP_DECISIONS_SCHEMA_URL,
    decision: {
      request_decision_id: crypto.randomUUID(),
      options: [
        {
          id: 'product-123',
          name: 'Cool Headphones',
          quantity: 2,
        },
      ],
    },
  };

  return Response.json({
    decision,
    decision_products,
    request_decision: mockRequestDecisionRadio,
    request_decision_checkbox: mockRequestDecisionCheckbox,
    request_decision_confirmation: mockRequestDecisionConfirmation,
    request_decision_products: mockRequestDecisionProducts,
  });
}
