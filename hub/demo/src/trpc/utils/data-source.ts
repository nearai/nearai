import { promises as fs } from 'fs';
import path from 'path';
import { z } from 'zod';

import { entryModel } from '@/lib/models';

type EntryModel = z.infer<typeof entryModel>;

const localEntryModel = entryModel.extend({
  id: z.number().default(0),
  namespace: z.string().default(''),
});

async function readMetadataJson(filePath: string) {
  try {
    const data = await fs.readFile(filePath, 'utf8');
    return localEntryModel.parse(JSON.parse(data));
  } catch (error) {
    console.error(`Error parsing local agent metadata: ${filePath}`, error);
    return null;
  }
}

export async function loadEntriesFromDirectory(
  registryDirectoryPath: string,
  _directoryPath: string | undefined = undefined,
  _results: EntryModel[] = [],
): Promise<EntryModel[]> {
  try {
    const directoryPath = _directoryPath ?? registryDirectoryPath;
    const files = await fs.readdir(directoryPath, { withFileTypes: true });

    await Promise.all(
      files.map(async (file) => {
        const isHidden = file.name.startsWith('.');
        if (isHidden) return;

        const filePath = path.join(directoryPath, file.name);

        if (file.isDirectory() || file.isSymbolicLink()) {
          await loadEntriesFromDirectory(
            registryDirectoryPath,
            filePath,
            _results,
          );
        } else if (file.name === 'metadata.json') {
          try {
            const metadata: EntryModel | null =
              await readMetadataJson(filePath);

            if (metadata) {
              metadata.id = _results.length + 1;

              const agentRelativePath = path.relative(
                registryDirectoryPath,
                directoryPath,
              );
              const agentPathParts = agentRelativePath.split(path.sep);

              if (
                agentPathParts.length > 0 &&
                agentPathParts[0]?.endsWith('.near')
              ) {
                // Ignore version from metadata if actual version in filePath is different
                metadata.version =
                  agentPathParts[agentPathParts.length - 1] ?? '';
                metadata.namespace = agentPathParts[0];
                _results.push(metadata);
              }
            }
          } catch (_error) {
            // Ignore error if agent.py doesn't exist or any other read error
          }
        }
      }),
    );
  } catch (error) {
    console.error(
      `Unexpected error reading local agent: ${_directoryPath}`,
      error,
    );
  }

  return _results;
}
