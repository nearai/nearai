import {
  Button,
  copyTextToClipboard,
  Dialog,
  Flex,
  PlaceholderStack,
  Tooltip,
  useDebouncedValue,
} from '@nearai/ui';
import { Copy, Eye, MarkdownLogo } from '@phosphor-icons/react';
import mime from 'mime';
import { useEffect, useState } from 'react';
import { type z } from 'zod';

import { type threadFileModel } from '@/lib/models';
import { useThreadsStore } from '@/stores/threads';
import { filePathIsImage, filePathToCodeLanguage } from '@/utils/file';

import { Code } from '../lib/Code';
import { Markdown } from '../lib/Markdown';

type Props = {
  filesById?: Record<string, z.infer<typeof threadFileModel>>;
};

export const ThreadFileModal = ({ filesById }: Props) => {
  const openedFileId = useThreadsStore((store) => store.openedFileId);
  const setOpenedFileId = useThreadsStore((store) => store.setOpenedFileId);

  const file = useDebouncedValue(
    filesById && openedFileId ? filesById[openedFileId] : undefined,
    25,
  );
  const type = mime.getType(file?.filename || '');

  const isImage = filePathIsImage(file?.filename);
  const language = file && filePathToCodeLanguage(file.filename);
  const isMarkdown = language === 'markdown';
  const [renderAsMarkdown, setRenderAsMarkdown] = useState(isMarkdown);

  useEffect(() => {
    if (type && file?.content instanceof Uint8Array) {
      const blob = new Blob([file.content], { type });
      const blobURL = URL.createObjectURL(blob);
      window.open(blobURL);
      setOpenedFileId(null);
    }
  }, [file, type, setOpenedFileId]);

  return (
    <Dialog.Root
      open={openedFileId !== null}
      onOpenChange={() => setOpenedFileId(null)}
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

            {!isImage && typeof file?.content === 'string' && (
              <Tooltip asChild content="Copy file content to clipboard">
                <Button
                  label="Copy to clipboard"
                  icon={<Copy />}
                  variant="secondary"
                  fill="ghost"
                  size="small"
                  onClick={() =>
                    file && copyTextToClipboard(file.content as string)
                  }
                  tabIndex={-1}
                />
              </Tooltip>
            )}
          </Flex>
        }
        size="l"
      >
        {file && typeof file.content === 'string' ? (
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
