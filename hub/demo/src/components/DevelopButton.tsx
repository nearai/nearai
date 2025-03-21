import {
  Button,
  Card,
  Dialog,
  Flex,
  HR,
  SvgIcon,
  Text,
  Tooltip,
} from '@nearai/ui';
import {
  BookOpenText,
  DownloadSimple,
  TerminalWindow,
} from '@phosphor-icons/react';
import { type CSSProperties, useState } from 'react';
import { type z } from 'zod';

import { idForEntry } from '@/lib/entries';
import { type entryModel } from '@/lib/models';
import { useAuthStore } from '@/stores/auth';
import { toTitleCase } from '@/utils/string';

import { Code } from './lib/Code';

type Props = {
  entry: z.infer<typeof entryModel> | undefined;
  style?: CSSProperties;
};

export const DevelopButton = ({ entry, style }: Props) => {
  const auth = useAuthStore((store) => store.auth);
  const isPermittedToViewSource =
    !entry?.details.private_source || auth?.accountId === entry.namespace;
  const [forkModalIsOpen, setForkModalIsOpen] = useState(false);

  if (!isPermittedToViewSource) return null;

  return (
    <>
      <Tooltip
        asChild
        content={`View instructions to download and develop this ${entry?.category} locally`}
      >
        <Button
          label="Develop"
          iconLeft={<SvgIcon size="xs" icon={<DownloadSimple />} />}
          size="small"
          variant="affirmative"
          style={style}
          onClick={() => setForkModalIsOpen(true)}
        />
      </Tooltip>

      {entry && (
        <Dialog.Root open={forkModalIsOpen} onOpenChange={setForkModalIsOpen}>
          <Dialog.Content
            title={`Develop ${toTitleCase(entry.category)}`}
            size="m"
          >
            <Flex direction="column" gap="l">
              <Flex direction="column" gap="m">
                <Flex align="center" gap="s">
                  <SvgIcon
                    icon={<TerminalWindow weight="fill" />}
                    color="cyan-9"
                  />
                  <Text color="sand-12" weight={600}>
                    NEAR AI CLI
                  </Text>
                </Flex>

                <Flex
                  align="center"
                  gap="l"
                  phone={{ direction: 'column', align: 'stretch' }}
                >
                  <Flex
                    direction="column"
                    gap="m"
                    style={{ marginRight: 'auto' }}
                  >
                    <Text>
                      Develop your {entry.category} locally in your favorite IDE
                      and deploy via the{' '}
                      <Tooltip content="View installation instructions">
                        <Text
                          href="https://github.com/nearai/nearai"
                          target="_blank"
                        >
                          NEAR AI CLI
                        </Text>
                      </Tooltip>
                    </Text>
                  </Flex>

                  <Button
                    label="View Docs"
                    iconLeft={<BookOpenText />}
                    href="https://docs.near.ai/agents/quickstart/"
                    target="_blank"
                  />
                </Flex>
              </Flex>

              <HR />

              <Flex direction="column" gap="m">
                <Text size="text-s">
                  <Text
                    size="text-s"
                    weight="600"
                    color="sand-12"
                    family="monospace"
                    as="span"
                  >
                    1.
                  </Text>{' '}
                  Download this {entry.category} locally:
                </Text>

                <Card background="sand-2" padding="s">
                  <Code
                    bleed
                    language="shell"
                    source={`nearai registry download ${idForEntry(entry)}`}
                    showLineNumbers={false}
                  />
                </Card>
              </Flex>

              <Flex direction="column" gap="m">
                <Text size="text-s">
                  <Text
                    size="text-s"
                    weight="600"
                    color="sand-12"
                    family="monospace"
                    as="span"
                  >
                    2.
                  </Text>{' '}
                  Navigate to the downloaded source code and make changes:
                </Text>

                <Card background="sand-2" padding="s">
                  <Code
                    bleed
                    language="shell"
                    source={`cd ~/.nearai/registry/${idForEntry(entry)}`}
                    showLineNumbers={false}
                  />
                </Card>
              </Flex>

              <Flex direction="column" gap="m">
                <Text size="text-s">
                  <Text
                    size="text-s"
                    weight="600"
                    color="sand-12"
                    family="monospace"
                    as="span"
                  >
                    3.
                  </Text>{' '}
                  Publish your changes:
                </Text>

                <Card background="sand-2" padding="s">
                  <Code
                    bleed
                    language="shell"
                    source={`nearai registry upload .`}
                    showLineNumbers={false}
                  />
                </Card>
              </Flex>
            </Flex>
          </Dialog.Content>
        </Dialog.Root>
      )}
    </>
  );
};
