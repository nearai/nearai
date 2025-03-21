'use client';

import { Button, copyTextToClipboard, Dropdown, SvgIcon } from '@nearai/ui';
import { BracketsCurly, Copy, DotsThree, Eye } from '@phosphor-icons/react';
import { type ReactNode, useState } from 'react';

import { Code } from '@/components/lib/Code';
import { stringToPotentialJson } from '@/utils/string';

import { useThreadMessageContent } from '../../ThreadMessageContentProvider';
import { Message as StandardMessage } from '../Message';

type Props = {
  children: ReactNode;
};

export const Message = ({ children }: Props) => {
  const { content } = useThreadMessageContent();
  const [viewSource, setViewSource] = useState(false);

  const returnJsonSource = () => {
    const json = stringToPotentialJson(content.text?.value ?? '');
    return json ? JSON.stringify(json, null, 2) : '';
  };

  return (
    <StandardMessage
      actions={
        <Dropdown.Root>
          <Dropdown.Trigger asChild>
            <Button
              label="Message Actions"
              icon={<DotsThree weight="bold" />}
              size="x-small"
              fill="ghost"
            />
          </Dropdown.Trigger>

          <Dropdown.Content sideOffset={0}>
            <Dropdown.Section>
              {viewSource ? (
                <Dropdown.Item onSelect={() => setViewSource(false)}>
                  <SvgIcon icon={<Eye />} />
                  View Component
                </Dropdown.Item>
              ) : (
                <Dropdown.Item onSelect={() => setViewSource(true)}>
                  <SvgIcon icon={<BracketsCurly />} />
                  View JSON
                </Dropdown.Item>
              )}

              <Dropdown.Item
                onSelect={() => copyTextToClipboard(returnJsonSource())}
              >
                <SvgIcon icon={<Copy />} />
                Copy To Clipboard (JSON)
              </Dropdown.Item>
            </Dropdown.Section>
          </Dropdown.Content>
        </Dropdown.Root>
      }
    >
      {viewSource ? (
        <Code bleed language="json" source={returnJsonSource()} />
      ) : (
        children
      )}
    </StandardMessage>
  );
};
