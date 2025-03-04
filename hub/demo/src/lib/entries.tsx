import { type z } from 'zod';

import { env } from '~/env';

import { type EntryCategory, type entryModel, optionalVersion } from './models';

export function primaryUrlForEntry(
  entry: Pick<z.infer<typeof entryModel>, 'namespace' | 'name' | 'category'>,
  version = 'latest',
) {
  let url: string | undefined;

  switch (entry.category as EntryCategory) {
    case 'agent':
      url = `/agents/${entry.namespace}/${entry.name}/${version}`;
      break;

    case 'benchmark':
      url = `/benchmarks/${entry.namespace}/${entry.name}/${version}`;
      break;

    case 'dataset':
      url = `/datasets/${entry.namespace}/${entry.name}/${version}`;
      break;

    case 'model':
      url = `/models/${entry.namespace}/${entry.name}/${version}`;
      break;
  }

  return url;
}

export function benchmarkEvaluationsUrlForEntry(
  entry: z.infer<typeof entryModel>,
) {
  let url: string | undefined;

  switch (entry.category as EntryCategory) {
    case 'agent':
    case 'benchmark':
    case 'model':
      url = `${primaryUrlForEntry(entry)}/evaluations`;
      break;
  }

  return url;
}

export function sourceUrlForEntry(
  entry: Pick<z.infer<typeof entryModel>, 'namespace' | 'name' | 'category'>,
  version = 'latest',
) {
  let url: string | undefined;

  switch (entry.category as EntryCategory) {
    case 'agent':
    case 'benchmark':
    case 'dataset':
    case 'model':
      url = `${primaryUrlForEntry(entry, version)}/source`;
      break;
  }

  return url;
}

export function rawFileSourceUrlForEntry(
  entry:
    | Pick<
        z.infer<typeof entryModel>,
        'namespace' | 'name' | 'category' | 'version'
      >
    | undefined,
  filePath: string | undefined,
) {
  if (!entry || !filePath) return;

  if (
    filePath.startsWith('https://') ||
    filePath.startsWith('http://') ||
    filePath.startsWith('data:image/') ||
    filePath.startsWith('#')
  )
    return filePath;

  filePath = filePath.replace(/^\.\//, '').replace(/^\//, '');

  const url = sourceUrlForEntry(entry, entry.version);
  if (!url) return;

  return `${env.NEXT_PUBLIC_BASE_URL}${url}/raw/${filePath}`;
}

export function idForEntry(
  entry: Pick<z.infer<typeof entryModel>, 'namespace' | 'name' | 'version'>,
) {
  return `${entry.namespace}/${entry.name}/${entry.version}`;
}

export function idMatchesEntry(id: string, entry: z.infer<typeof entryModel>) {
  return (
    id.startsWith(`${entry.namespace}/${entry.name}/`) ||
    id === `${entry.namespace}/${entry.name}`
  );
}

export function parseEntryId(id: string) {
  const segments = id.split('/');
  const namespace = segments[0];
  const name = segments[1];

  let version = segments[2] || 'latest';
  if (version === '*') version = 'latest';

  if (!namespace || !name) {
    throw new Error(
      `Attempted to parse invalid entry ID: ${id} (expected format is "namespace/name" or "namespace/name/version")`,
    );
  }

  return { namespace, name, version };
}

export function parseEntryIdWithOptionalVersion(id: string) {
  const segments = parseEntryId(id);
  const version = optionalVersion.parse(segments.version);
  return { ...segments, version };
}
