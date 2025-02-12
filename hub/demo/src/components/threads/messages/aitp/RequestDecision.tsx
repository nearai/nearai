'use client';

import { type z } from 'zod';

import { RequestDecisionCheckbox } from './RequestDecisionCheckbox';
import { RequestDecisionConfirmation } from './RequestDecisionConfirmation';
import { RequestDecisionProducts } from './RequestDecisionProducts';
import { type requestDecisionSchema } from './schema/decision';

type Props = {
  contentId: string;
  content: z.infer<typeof requestDecisionSchema>['request_decision'];
};

export const RequestDecision = ({ content, contentId }: Props) => {
  const type = content.type;

  console.log(content);

  if (type === 'products') {
    return <RequestDecisionProducts content={content} contentId={contentId} />;
  }

  if (type === 'confirmation') {
    return (
      <RequestDecisionConfirmation content={content} contentId={contentId} />
    );
  }

  return <RequestDecisionCheckbox content={content} contentId={contentId} />;
};
