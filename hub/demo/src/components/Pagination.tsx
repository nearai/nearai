'use client';

import { Button, Flex, Text } from '@nearai/ui';
import { ArrowLeft, ArrowRight } from '@phosphor-icons/react';

import { type ClientPagination } from '@/hooks/pagination';

type Props = Pick<
  ClientPagination,
  | 'previousPage'
  | 'nextPage'
  | 'firstPage'
  | 'lastPage'
  | 'createPageQueryPath'
  | 'totalPagesTruncatedAsArray'
  | 'page'
>;

export const Pagination = ({
  previousPage,
  nextPage,
  firstPage,
  lastPage,
  createPageQueryPath,
  totalPagesTruncatedAsArray,
  page,
}: Props) => {
  return (
    <Flex align="center" justify="space-between" gap="m">
      <Button
        label="Previous Page"
        icon={<ArrowLeft />}
        href={
          previousPage
            ? createPageQueryPath({
                page: previousPage.toString(),
              })
            : undefined
        }
        disabled={!previousPage}
      />

      <Flex align="center" justify="center" gap="m" wrap="wrap">
        {firstPage && !totalPagesTruncatedAsArray.includes(firstPage) && (
          <>
            <Text
              decoration="none"
              href={createPageQueryPath({
                page: firstPage.toString(),
              })}
              size="text-s"
            >
              {firstPage}
            </Text>
            <Text size="text-xs">...</Text>
          </>
        )}

        {totalPagesTruncatedAsArray.map((p) => (
          <Text
            color={p === page ? 'sand-12' : undefined}
            decoration={p === page ? 'underline' : 'none'}
            href={createPageQueryPath({ page: p.toString() })}
            size="text-s"
            key={p}
          >
            {p}
          </Text>
        ))}

        {lastPage && !totalPagesTruncatedAsArray.includes(lastPage) && (
          <>
            <Text size="text-xs">...</Text>
            <Text
              decoration="none"
              href={createPageQueryPath({
                page: lastPage.toString(),
              })}
              size="text-s"
            >
              {lastPage}
            </Text>
          </>
        )}
      </Flex>

      <Button
        label="Next Page"
        icon={<ArrowRight />}
        href={
          nextPage
            ? createPageQueryPath({ page: nextPage.toString() })
            : undefined
        }
        disabled={!nextPage}
      />
    </Flex>
  );
};
