'use client';

import {
  Button,
  Card,
  CardList,
  Flex,
  Input,
  PlaceholderStack,
  Text,
} from '@nearai/ui';
import { Minus, Plus } from '@phosphor-icons/react';
import { useEffect, useRef } from 'react';
import { type z } from 'zod';

import { useEntriesSearch } from '@/hooks/entries';
import { idForEntry } from '@/lib/entries';
import { type EntryCategory, type entryModel } from '@/lib/models';
import { trpc } from '@/trpc/TRPCProvider';

import { EntryCard } from './EntryCard';

export type EntrySelectorOnSelectHandler = (
  item: z.infer<typeof entryModel>,
  selected: boolean,
) => unknown;

type Props = {
  category: EntryCategory;
  description?: string;
  selectedIds: string[];
  onSelect: EntrySelectorOnSelectHandler;
};

export const EntrySelector = ({
  category,
  description,
  selectedIds,
  onSelect,
}: Props) => {
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const entriesQuery = trpc.hub.entries.useQuery({ category });

  const { searched, setSearchQuery } = useEntriesSearch(entriesQuery.data);

  searched?.sort((a, b) => {
    let sort = b.num_stars - a.num_stars;
    if (sort === 0) sort = a.name.localeCompare(b.name);
    return sort;
  });

  useEffect(() => {
    setTimeout(() => {
      searchInputRef.current?.focus();
    });
  }, []);

  return (
    <Flex direction="column" gap="l">
      {description && <Text>{description}</Text>}

      <Input
        type="search"
        name="search"
        placeholder="Search"
        onInput={(event) => setSearchQuery(event.currentTarget.value)}
        ref={searchInputRef}
      />

      {searched ? (
        <CardList>
          {searched.map((entry) => (
            <EntryCard
              linksOpenNewTab
              entry={entry}
              key={entry.id}
              footer={
                <div>
                  {selectedIds.includes(idForEntry(entry)) ? (
                    <Button
                      iconLeft={<Minus />}
                      label="Remove"
                      variant="secondary"
                      size="small"
                      onClick={() => onSelect(entry, false)}
                    />
                  ) : (
                    <Button
                      iconLeft={<Plus />}
                      label="Include"
                      variant="affirmative"
                      size="small"
                      onClick={() => onSelect(entry, true)}
                    />
                  )}
                </div>
              }
            />
          ))}

          {!searched.length && (
            <Card>
              <Text>No matching results. Try a different search?</Text>
            </Card>
          )}
        </CardList>
      ) : (
        <PlaceholderStack />
      )}
    </Flex>
  );
};
