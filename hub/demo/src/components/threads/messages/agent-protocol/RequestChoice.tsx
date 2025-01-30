'use client';

import { type z } from 'zod';

import { RequestChoiceCheckbox } from './RequestChoiceCheckbox';
import { RequestChoiceConfirmation } from './RequestChoiceConfirmation';
import { RequestChoiceProducts } from './RequestChoiceProducts';
import { type requestChoiceSchema } from './schema';

type Props = {
  contentId: string;
  content: z.infer<typeof requestChoiceSchema>['request_choice'];
};

export const RequestChoice = ({ content, contentId }: Props) => {
  const type = content.type;

  if (type === 'products') {
    return <RequestChoiceProducts content={content} contentId={contentId} />;
  }

  if (type === 'confirmation') {
    return (
      <RequestChoiceConfirmation content={content} contentId={contentId} />
    );
  }

  return <RequestChoiceCheckbox content={content} contentId={contentId} />;
};
