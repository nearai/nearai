import { type CodeLanguage } from '~/components/lib/Code';

export function filePathToCodeLanguage(
  path: string | undefined | null,
): CodeLanguage {
  const extension = path?.split('.').at(-1);
  if (!extension) return '';

  switch (extension) {
    case 'css':
      return 'css';
    case 'html':
      return 'html';
    case 'js':
      return 'javascript';
    case 'py':
      return 'python';
    case 'md':
      return 'markdown';
  }

  return '';
}

export function filePathIsImage(path: string | undefined | null) {
  const extension = path?.split('.').at(-1) ?? '';
  const isImage = ['png', 'jpg', 'gif', 'webp'].includes(extension);
  return isImage;
}