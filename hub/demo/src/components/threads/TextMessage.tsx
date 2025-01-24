'use client';

import {
  Button,
  Card,
  copyTextToClipboard,
  Dropdown,
  Flex,
  SvgIcon,
  Text,
} from '@near-pagoda/ui';
import { Copy, DotsThree, Eye, MarkdownLogo } from '@phosphor-icons/react';
import { useState } from 'react';
import { type z } from 'zod';

import {
  type threadMessageModel,
  type threadMessageModelContentText,
} from '~/lib/models';

import { Markdown } from '../lib/Markdown';

type Props = {
  content: z.infer<typeof threadMessageModelContentText>;
  role: z.infer<typeof threadMessageModel>['role'];
};

export const TextMessage = ({ content, role }: Props) => {
  const [renderAsMarkdown, setRenderAsMarkdown] = useState(true);
  const text = content.text.value;

  return (
    <>
      {role === 'user' ? (
        <Card animateIn background="sand-2" style={{ alignSelf: 'end' }}>
          {renderAsMarkdown ? <Markdown content={text} /> : <Text>{text}</Text>}
        </Card>
      ) : (
        <Card animateIn>
          {renderAsMarkdown ? <Markdown content={text} /> : <Text>{text}</Text>}

          <Flex align="center" gap="m">
            <Text
              size="text-xs"
              style={{
                textTransform: 'capitalize',
                marginRight: 'auto',
              }}
            >
              - {role}
            </Text>

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
                  <Dropdown.Item onSelect={() => copyTextToClipboard(text)}>
                    <SvgIcon icon={<Copy />} />
                    Copy To Clipboard
                  </Dropdown.Item>

                  {renderAsMarkdown ? (
                    <Dropdown.Item onSelect={() => setRenderAsMarkdown(false)}>
                      <SvgIcon icon={<MarkdownLogo />} />
                      View Markdown Source
                    </Dropdown.Item>
                  ) : (
                    <Dropdown.Item onSelect={() => setRenderAsMarkdown(true)}>
                      <SvgIcon icon={<Eye />} />
                      Render Markdown
                    </Dropdown.Item>
                  )}
                </Dropdown.Section>
              </Dropdown.Content>
            </Dropdown.Root>
          </Flex>
        </Card>
      )}
    </>
  );
};
