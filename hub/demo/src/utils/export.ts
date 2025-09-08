import { TarWriter } from '@gera2ld/tarjs';
import { type z } from 'zod';

import { env } from '@/env';
import { type entryModel } from '@/lib/models';

export type ExportProgress = {
  current: number;
  total: number;
  currentFile?: string;
  error?: string;
};

/**
 * Exports an agent as a tar archive
 * @param entry The agent entry to export
 * @param filePaths List of file paths to include in the export
 * @param onProgress Optional callback for progress updates
 * @returns A blob containing the tar archive
 */
export async function exportAgentAsTar(
  entry: z.infer<typeof entryModel>,
  filePaths: string[],
  onProgress?: (progress: ExportProgress) => void,
): Promise<Blob> {
  const tar = new TarWriter();
  const folderName =
    `${entry.namespace}-${entry.name}-${entry.version}`.replace(
      /[^a-zA-Z0-9-_]/g,
      '_',
    );

  // Report initial progress
  onProgress?.({
    current: 0,
    total: filePaths.length,
  });

  // Fetch all files and add them to the tar archive
  for (let i = 0; i < filePaths.length; i++) {
    const filePath = filePaths[i];

    try {
      onProgress?.({
        current: i,
        total: filePaths.length,
        currentFile: filePath,
      });

      // Fetch the file content
      const response = await fetch(
        `${env.NEXT_PUBLIC_BASE_URL}/agents/${entry.namespace}/${entry.name}/${entry.version}/source/raw/${filePath}`,
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch file: ${filePath}`);
      }

      const content = await response.arrayBuffer();
      const uint8Array = new Uint8Array(content);

      // Add file to tar archive with folder structure
      tar.addFile(`${folderName}/${filePath}`, uint8Array);
    } catch (error) {
      console.error(`Error fetching file ${filePath}:`, error);
      onProgress?.({
        current: i,
        total: filePaths.length,
        currentFile: filePath,
        error: `Failed to fetch ${filePath}`,
      });
    }
  }

  // Add a README file with export information
  const readmeContent = `# ${entry.name}

Exported from NEAR AI Hub
Namespace: ${entry.namespace}
Version: ${entry.version}
Category: ${entry.category}
Export Date: ${new Date().toISOString()}

## Description
${entry.description || 'No description available'}

## Tags
${entry.tags.join(', ') || 'No tags'}

## How to Use
This agent was exported from the NEAR AI Hub. To use it:
1. Extract this archive to your desired location
2. Follow the agent's specific setup instructions in its documentation
3. Install any required dependencies

For more information, visit: https://near.ai
`;

  const encoder = new TextEncoder();
  tar.addFile(`${folderName}/README_EXPORT.md`, encoder.encode(readmeContent));

  // Generate the tar blob
  const tarBlob = await tar.write();

  // Report completion
  onProgress?.({
    current: filePaths.length,
    total: filePaths.length,
  });

  return tarBlob;
}

/**
 * Downloads a blob as a file
 * @param blob The blob to download
 * @param filename The name of the file to save as
 */
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
