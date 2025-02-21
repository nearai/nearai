'use client';

import { type z } from 'zod';

import { RequestDecisionCheckbox } from './RequestDecisionCheckbox';
import { RequestDecisionConfirmation } from './RequestDecisionConfirmation';
import { RequestDecisionProducts } from './RequestDecisionProducts';
import { type requestDecisionSchema } from './schema/decisions';

type Props = {
  content: z.infer<typeof requestDecisionSchema>['request_decision'];
};

export const RequestDecision = ({ content }: Props) => {
  const type = content.type;

  if (type === 'products') {
    return <RequestDecisionProducts content={content} />;
  }

  if (type === 'confirmation') {
    return <RequestDecisionConfirmation content={content} />;
  }

  return <RequestDecisionCheckbox content={content} />;
};
