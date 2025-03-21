'use client';

import { useRef } from 'react';

import { Code } from '@/components/lib/Code';

import { Data } from './aitp/Data';
import { Decision } from './aitp/Decision';
import { PaymentAuthorization } from './aitp/PaymentAuthorization';
import { PaymentResult } from './aitp/PaymentResult';
import { Quote } from './aitp/Quote';
import { RequestData } from './aitp/RequestData';
import { RequestDecision } from './aitp/RequestDecision';
import { parseJsonWithAitpSchema } from './aitp/schema';
import { Message } from './Message';

type Props = {
  json: Record<string, unknown>;
};

export const JsonMessage = ({ json }: Props) => {
  const hasWarned = useRef(false);
  const aitp = parseJsonWithAitpSchema(json);

  if ('data' in aitp) {
    return <Data content={aitp.data} />;
  } else if ('decision' in aitp) {
    return <Decision content={aitp.decision} />;
  } else if ('payment_authorization' in aitp) {
    return <PaymentAuthorization content={aitp.payment_authorization} />;
  } else if ('payment_result' in aitp) {
    return <PaymentResult content={aitp.payment_result} />;
  } else if ('quote' in aitp) {
    return <Quote content={aitp.quote} />;
  } else if ('request_data' in aitp) {
    return <RequestData content={aitp.request_data} />;
  } else if ('request_decision' in aitp) {
    return <RequestDecision content={aitp.request_decision} />;
  }

  if (!hasWarned.current) {
    console.warn(
      `JSON message failed to match AITP schema. Will render as JSON codeblock.`,
      aitp.error,
    );
    hasWarned.current = true;
  }

  return (
    <Message>
      <Code bleed language="json" source={JSON.stringify(json, null, 2)} />
    </Message>
  );
};
