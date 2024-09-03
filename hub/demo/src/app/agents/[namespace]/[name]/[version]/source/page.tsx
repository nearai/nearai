'use client';

import { Copy, Folder } from '@phosphor-icons/react';
import { useEffect, useState } from 'react';

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
import { useCurrentResource, useResourceParams } from '~/hooks/resources';
import { useQueryParams } from '~/hooks/url';
import { api } from '~/trpc/react';
import { copyTextToClipboard } from '~/utils/clipboard';

export default function AgentSourcePage() {
  const { createQueryPath, queryParams } = useQueryParams(['file']);
  const { currentResource } = useCurrentResource('agent');
  const params = useResourceParams();
  const filePathsQuery = api.hub.listFilePaths.useQuery(params);
  const activeFilePath = queryParams.file ?? filePathsQuery.data?.[0] ?? '';
  const fileQuery = api.hub.loadFileByPath.useQuery(
    { ...params, filePath: activeFilePath },
    {
      enabled: !!activeFilePath,
    },
  );

  const [sidebarOpenForSmallScreens, setSidebarOpenForSmallScreens] =
    useState(false);

  const openedFile =
    activeFilePath === fileQuery.data?.path ? fileQuery.data : undefined;

  useEffect(() => {
    setSidebarOpenForSmallScreens(false);
  }, [queryParams.file]);

  if (!currentResource) return null;

  return (
    <>
      <Sidebar.Root>
        <Sidebar.Sidebar
          openForSmallScreens={sidebarOpenForSmallScreens}
          setOpenForSmallScreens={setSidebarOpenForSmallScreens}
        >
          <Text size="text-l">Files</Text>

          {filePathsQuery.data ? (
            <CardList>
              {filePathsQuery.data?.map((path) => (
                <Card
                  padding="s"
                  href={createQueryPath({ file: path })}
                  key={path}
                  background={path === activeFilePath ? 'sand-0' : 'sand-2'}
                >
                  <Text
                    size="text-s"
                    color="violet-11"
                    weight={500}
                    clampLines={1}
                  >
                    {path}
                  </Text>
                </Card>
              ))}
            </CardList>
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
            />
          </Flex>

          {openedFile ? (
            <Code
              source={openedFile.content}
              language={filePathToCodeLanguage(openedFile.path)}
            />
          ) : (
            <PlaceholderCard />
          )}
        </Sidebar.Main>
      </Sidebar.Root>
    </>
  );
}
