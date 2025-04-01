import path from 'path';
import { z } from 'zod';

import { env } from '@/env';
import { type entriesModel, entryCategory, entryModel } from '@/lib/models';

import { type AppRouterContext } from '../router';
import { loadEntriesFromDirectory } from './data-source';

export const fetchEntriesInputSchema = z.object({
  category: entryCategory.optional(),
  forkOf: z
    .object({
      name: z.string(),
      namespace: z.string(),
    })
    .optional(),
  limit: z.number().default(10_000),
  namespace: z.string().optional(),
  showLatestVersion: z.boolean().default(true),
  starredBy: z.string().optional(),
  tags: z.string().array().optional(),
});

export async function fetchEntries(
  ctx: Pick<AppRouterContext, 'authorization' | 'signature'>,
  input: z.infer<typeof fetchEntriesInputSchema>,
) {
  const url = new URL(`${env.ROUTER_URL}/registry/list_entries`);

  url.searchParams.append('total', `${input.limit}`);
  url.searchParams.append('show_latest_version', `${input.showLatestVersion}`);

  if (input.category) url.searchParams.append('category', input.category);

  if (input.namespace) url.searchParams.append('namespace', input.namespace);

  if (input.tags) url.searchParams.append('tags', input.tags.join(','));

  if (input.category == 'agent' && env.DATA_SOURCE == 'local_files') {
    if (!env.HOME)
      throw new Error(
        'Missing required HOME environment variable for serving local files',
      );
    const registryPath = path.join(env.HOME, '.nearai', 'registry');
    return await loadEntriesFromDirectory(registryPath);
  }

  if (input.starredBy) url.searchParams.append('starred_by', input.starredBy);

  if (input.forkOf) {
    url.searchParams.append('fork_of_namespace', input.forkOf.namespace);
    url.searchParams.append('fork_of_name', input.forkOf.name);
  }

  if (ctx.signature) {
    url.searchParams.append('star_point_of_view', ctx.signature.account_id);
  }

  const response = await fetch(url.toString(), {
    method: 'POST',
  });

  const data: unknown = await response.json().catch(() => response.text());

  if (!response.ok || !Array.isArray(data)) throw data;

  /*
    Unfortunately, we can't rely on fetchWithZod() for this method. If the endpoint 
    returns a single record that didn't match our expected "entries" schema, 
    all of the data would be thrown out. Instead, we loop over each returned item and 
    parse the entries one at a time - only omitting entries that aren't valid instead 
    of throwing an error for the entire list.
  */

  const list: z.infer<typeof entriesModel> = data
    .map((item) => {
      const parsed = entryModel.safeParse(item);
      if (parsed.data?.tags) {
        parsed.data.tags.sort();
      }
      return parsed.data;
    })
    .filter((entry) => !!entry);

  return list;
}

export const fetchEntryInputSchema = z.object({
  category: entryCategory,
  namespace: z.string(),
  name: z.string(),
  version: z.string(),
});

export async function fetchEntry(
  ctx: Pick<AppRouterContext, 'authorization' | 'signature'>,
  input: z.infer<typeof fetchEntryInputSchema>,
) {
  const entries = await fetchEntries(ctx, {
    ...input,
    limit: 10_000,
    showLatestVersion: false,
  });

  const versions = entries.filter((item) => item.name === input.name);

  versions?.sort((a, b) => b.id - a.id);

  const entry =
    input.version === 'latest'
      ? versions?.[0]
      : versions?.find((item) => item.version === input.version);

  return {
    entry,
    versions,
  };
}

export async function fetchEntryMetadataJson(
  ctx: Pick<AppRouterContext, 'authorization' | 'signature'>,
  input: z.infer<typeof fetchEntryInputSchema>,
) {
  const { entry } = await fetchEntry(ctx, input);

  if (!entry)
    throw new Error('Failed to find entry details to compute metadata.json');

  const metadata = {
    category: entry.category,
    namespace: entry.namespace,
    name: entry.name,
    version: entry.version,
    description: entry.description,
    tags: entry.tags,
    details: entry.details,
  };

  return {
    json: metadata,
    stringified: JSON.stringify(metadata, null, 2),
  };
}
