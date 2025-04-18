'use client';

import { Button, copyTextToClipboard, Dropdown, SvgIcon } from '@nearai/ui';
import { Copy, DotsThree, Eye, MarkdownLogo } from '@phosphor-icons/react';
import { useState } from 'react';
import { type z } from 'zod';

import { Code } from '@/components/lib/Code';
import { Markdown } from '@/components/lib/Markdown';
import { type threadMessageContentModel } from '@/lib/models';

import { Message } from './Message';

type Props = {
  text: NonNullable<z.infer<typeof threadMessageContentModel>['text']>;
};

export const TextMessage = (props: Props) => {
  const [viewSource, setViewSource] = useState(false);
  const text = props.text.value;

  return (
    <Message
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
                  View Rendered Markdown
                </Dropdown.Item>
              ) : (
                <Dropdown.Item onSelect={() => setViewSource(true)}>
                  <SvgIcon icon={<MarkdownLogo />} />
                  View Markdown Source
                </Dropdown.Item>
              )}

              <Dropdown.Item onSelect={() => copyTextToClipboard(text)}>
                <SvgIcon icon={<Copy />} />
                Copy To Clipboard (Markdown)
              </Dropdown.Item>
            </Dropdown.Section>
          </Dropdown.Content>
        </Dropdown.Root>
      }
    >
      {text.trim() && (
        <>
          {viewSource ? (
            <Code bleed language="markdown" source={text} />
          ) : (
            <Markdown content={text} />
          )}
        </>
      )}
    </Message>
  );
};
