import {
  Button,
  copyTextToClipboard,
  Dialog,
  Flex,
  PlaceholderStack,
  Tooltip,
  useDebouncedValue,
} from '@near-pagoda/ui';
import { Copy, Eye, MarkdownLogo } from '@phosphor-icons/react';
import { useState } from 'react';
import { type z } from 'zod';

import { type threadFileModel } from '~/lib/models';
import { filePathIsImage, filePathToCodeLanguage } from '~/utils/file';

import { Code } from '../lib/Code';
import { Markdown } from '../lib/Markdown';

type Props = {
  filesByName?: Record<string, z.infer<typeof threadFileModel>>;
  openedFileName: string | null;
  setOpenedFileName: (id: string | null) => void;
};

export const ThreadFileModal = ({
  filesByName,
  openedFileName,
  setOpenedFileName,
}: Props) => {
  const file = useDebouncedValue(
    filesByName && openedFileName ? filesByName[openedFileName] : undefined,
    25,
  );

  const isImage = filePathIsImage(file?.filename);
  const language = file && filePathToCodeLanguage(file.filename);
  const isMarkdown = language === 'markdown';
  const [renderAsMarkdown, setRenderAsMarkdown] = useState(isMarkdown);

  return (
    <Dialog.Root
      open={openedFileName !== null}
      onOpenChange={() => setOpenedFileName(null)}
    >
      <Dialog.Content
        title={file?.filename ?? '...'}
        header={
          <Flex style={{ marginLeft: 'auto' }} gap="xs">
            {isMarkdown && (
              <>
                {renderAsMarkdown ? (
                  <Tooltip asChild content="View markdown source">
                    <Button
                      label="View markdown source"
                      icon={<MarkdownLogo />}
                      variant="secondary"
                      fill="ghost"
                      size="small"
                      onClick={() => setRenderAsMarkdown(false)}
                      tabIndex={-1}
                    />
                  </Tooltip>
                ) : (
                  <Tooltip asChild content="Render markdown">
                    <Button
                      label="Render markdown"
                      icon={<Eye />}
                      variant="secondary"
                      fill="ghost"
                      size="small"
                      onClick={() => setRenderAsMarkdown(true)}
                      tabIndex={-1}
                    />
                  </Tooltip>
                )}
              </>
            )}

            {!isImage && (
              <Tooltip asChild content="Copy file content to clipboard">
                <Button
                  label="Copy to clipboard"
                  icon={<Copy />}
                  variant="secondary"
                  fill="ghost"
                  size="small"
                  onClick={() => file && copyTextToClipboard(file.content)}
                  tabIndex={-1}
                />
              </Tooltip>
            )}
          </Flex>
        }
        size="l"
      >
        {file ? (
          isImage ? (
            <img src={file.content} alt={file.filename} />
          ) : (
            <>
              {renderAsMarkdown ? (
                <Markdown content={file.content} />
              ) : (
                <Code
                  bleed
                  showCopyButton={false}
                  source={file.content}
                  language={filePathToCodeLanguage(file.filename)}
                />
              )}
            </>
          )
        ) : (
          <PlaceholderStack />
        )}
      </Dialog.Content>
    </Dialog.Root>
  );
};
