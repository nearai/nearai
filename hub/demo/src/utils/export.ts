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

Exported from NEAR AI Hub (Service Discontinued)
Namespace: ${entry.namespace}
Version: ${entry.version}
Category: ${entry.category}
Export Date: ${new Date().toISOString()}

## Description
${entry.description || 'No description available'}

## Tags
${entry.tags.join(', ') || 'No tags'}

## ⚠️ Important: NEAR AI Hub Has Been Discontinued

The NEAR AI Hub service has been permanently shut down. This export contains all your agent's code and configuration files, but you will need to migrate to alternative AI platforms to continue using your agent.

## Migration Options

### 1. Alternative AI Providers
- **OpenAI:** https://platform.openai.com (GPT-4, GPT-3.5)
- **Anthropic:** https://www.anthropic.com (Claude)
- **Google AI:** https://ai.google.dev (Gemini)
- **Hugging Face:** https://huggingface.co

### 2. Open Source Frameworks
- **LangChain:** https://langchain.com - Multi-provider agent framework
- **AutoGen:** https://github.com/microsoft/autogen - Multi-agent conversations
- **CrewAI:** https://www.crewai.com - Agent orchestration

### 3. Local LLMs
- **Ollama:** https://ollama.ai - Run models locally
- **LM Studio:** https://lmstudio.ai - Desktop LLM app
- **Text Generation WebUI:** https://github.com/oobabooga/text-generation-webui

## How to Migrate Your Agent

1. **Extract this archive** to your desired location
2. **Review the agent code** in the extracted files
3. **Choose a new provider** from the options above
4. **Update API calls** to use the new provider's SDK
5. **Replace NEAR AI imports** with equivalent libraries
6. **Set up authentication** for your chosen provider
7. **Test your migrated agent** thoroughly

## What's Included
- All agent source code files
- Configuration and metadata
- Custom prompts and templates
- Any additional resources

Note: This agent was exported from NEAR AI Hub before the complete service shutdown. You will need to adapt the code to work with your chosen alternative platform.
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
