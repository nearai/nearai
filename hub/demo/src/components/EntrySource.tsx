'use client';

import { Copy, Folder } from '@phosphor-icons/react';
import { useEffect, useState } from 'react';
import { type z } from 'zod';

import { BreakpointDisplay } from '~/components/lib/BreakpointDisplay';
import { Button } from '~/components/lib/Button';
import { Card, CardList } from '~/components/lib/Card';
import { Code, filePathToCodeLanguage } from '~/components/lib/Code';
import { Flex } from '~/components/lib/Flex';
import {
  PlaceholderCard,
  PlaceholderStack,
} from '~/components/lib/Placeholder';
import { Sidebar } from '~/components/lib/Sidebar';
import { Text } from '~/components/lib/Text';
import { useEntryParams } from '~/hooks/entries';
import { useQueryParams } from '~/hooks/url';
import { type entryModel } from '~/lib/models';
import { api } from '~/trpc/react';
import { copyTextToClipboard } from '~/utils/clipboard';

const METADATA_FILE_PATH = 'metadata.json';

type Props = {
  entry: z.infer<typeof entryModel>;
};

export const EntrySource = ({ entry }: Props) => {
  const { createQueryPath, queryParams } = useQueryParams(['file']);
  const params = useEntryParams();
  const filePathsQuery = api.hub.filePaths.useQuery(params);
  const activeFilePath = queryParams.file ?? filePathsQuery.data?.[0] ?? '';
  const activeFileIsCompressed =
    activeFilePath.endsWith('.zip') || activeFilePath.endsWith('.tar');
  const fileQuery = api.hub.file.useQuery(
    { ...params, filePath: activeFilePath },
    {
      enabled:
        !!activeFilePath &&
        activeFilePath !== METADATA_FILE_PATH &&
        !activeFileIsCompressed,
    },
  );

  const [sidebarOpenForSmallScreens, setSidebarOpenForSmallScreens] =
    useState(false);

  let openedFile =
    activeFilePath === fileQuery.data?.path ? fileQuery.data : undefined;
  if (activeFilePath === METADATA_FILE_PATH) {
    const metadata = {
      category: entry.category,
      name: entry.name,
      namespace: entry.namespace,
      tags: entry.tags,
      details: entry.details,
    };
    openedFile = {
      content: JSON.stringify(metadata ?? '{}', null, 2),
      path: METADATA_FILE_PATH,
    };
  }

  useEffect(() => {
    setSidebarOpenForSmallScreens(false);
  }, [queryParams.file]);

  return (
    <>
      <Sidebar.Root>
        <Sidebar.Sidebar
          openForSmallScreens={sidebarOpenForSmallScreens}
          setOpenForSmallScreens={setSidebarOpenForSmallScreens}
        >
          <Text size="text-xs" weight={600} uppercase>
            Files
          </Text>

          {filePathsQuery.data ? (
            <Sidebar.SidebarContentBleed>
              <CardList>
                {filePathsQuery.data?.map((path) => (
                  <Card
                    padding="s"
                    paddingInline="m"
                    href={createQueryPath({ file: path })}
                    key={path}
                    background={path === activeFilePath ? 'sand-0' : 'sand-2'}
                  >
                    <Text
                      size="text-s"
                      color="violet-11"
                      clickableHighlight
                      weight={500}
                      clampLines={1}
                    >
                      {path}
                    </Text>
                  </Card>
                ))}
              </CardList>
            </Sidebar.SidebarContentBleed>
          ) : (
            <PlaceholderStack />
          )}
        </Sidebar.Sidebar>

        <Sidebar.Main>
          <Flex align="center" gap="m" style={{ marginBlock: '-3px' }}>
            <Text size="text-l" style={{ marginRight: 'auto' }}>
              {activeFilePath}
            </Text>

            <BreakpointDisplay show="sidebar-small-screen">
              <Button
                label="View All Files"
                icon={<Folder />}
                size="small"
                fill="outline"
                onClick={() => setSidebarOpenForSmallScreens(true)}
              />
            </BreakpointDisplay>

            <Button
              label="Copy file to clipboard"
              icon={<Copy />}
              size="small"
              fill="outline"
              onClick={() =>
                openedFile && copyTextToClipboard(openedFile.content)
              }
              disabled={activeFileIsCompressed}
            />
          </Flex>
          {activeFileIsCompressed ? (
            <Text>This file type {`doesn't`} have a source preview.</Text>
          ) : (
            <>
              {openedFile ? (
                <Code
                  source={openedFile.content}
                  language={filePathToCodeLanguage(openedFile.path)}
                />
              ) : (
                <PlaceholderCard />
              )}
            </>
          )}
        </Sidebar.Main>
      </Sidebar.Root>
    </>
  );
};