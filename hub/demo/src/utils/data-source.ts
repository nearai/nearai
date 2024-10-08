import { promises as fs } from 'fs';
import path from 'path';
import { type z } from 'zod';

import { entryModel } from '~/lib/models';

type EntryModel = z.infer<typeof entryModel>;

export async function readMetadataJson(
  filePath: string,
): Promise<EntryModel | null> {
  try {
    const data = await fs.readFile(filePath, 'utf8');
    return entryModel.parse(JSON.parse(data));
  } catch (error) {
    console.error(`Error parsing local agent metadata: ${filePath}`, error);
    return null;
  }
}

export async function processDirectory(
  dirPath: string,
  results: EntryModel[],
  registryPath: string,
): Promise<EntryModel[]> {
  try {
    const files = await fs.readdir(dirPath, { withFileTypes: true });

    await Promise.all(
      files.map(async (file) => {
        const isHidden = file.name.startsWith('.');
        if (isHidden) return;

        const filePath = path.join(dirPath, file.name);

        if (file.isDirectory()) {
          await processDirectory(filePath, results, registryPath);
        } else if (file.name === 'metadata.json') {
          try {
            const metadata: EntryModel | null =
              await readMetadataJson(filePath);

            if (metadata) {
              metadata.id = results.length + 1;

              const agentRelativePath = path.relative(registryPath, dirPath);
              const agentPathParts = agentRelativePath.split(path.sep);

              if (
                agentPathParts.length > 0 &&
                agentPathParts[0]?.endsWith('.near')
              ) {
                // Ignore version from metadata if actual version in filePath is different
                metadata.version =
                  agentPathParts[agentPathParts.length - 1] ?? '';
                metadata.namespace = agentPathParts[0];
                results.push(metadata);
              }
            }
          } catch (error) {
            // Ignore error if agent.py doesn't exist or any other read error
          }
        }
      }),
    );
  } catch (error) {
    console.error(`Unexpected error reading local agent: ${dirPath}`, error);
  }

  return results;
}
