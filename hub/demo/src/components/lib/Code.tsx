`use client`;

/* eslint-disable @typescript-eslint/no-unsafe-assignment */

import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';
import SyntaxHighlighter from 'react-syntax-highlighter';
import {
  atomOneDark,
  atomOneLight,
} from 'react-syntax-highlighter/dist/esm/styles/hljs';

import s from './Code.module.scss';

type CodeLanguage =
  | 'css'
  | 'html'
  | 'javascript'
  | 'markdown'
  | 'python'
  | 'json'
  // eslint-disable-next-line @typescript-eslint/ban-types
  | (string & {})
  | undefined
  | null;

type Props = {
  bleed?: boolean;
  language: CodeLanguage;
  showLineNumbers?: boolean;
  source: string | undefined | null;
};

export const Code = ({
  bleed,
  language,
  showLineNumbers = true,
  source,
}: Props) => {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  const style =
    mounted && resolvedTheme === 'dark' ? atomOneDark : atomOneLight;

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className={s.code} data-bleed={bleed}>
      {source && (
        <SyntaxHighlighter
          language={language ?? ''}
          style={style}
          showLineNumbers={language === 'markdown' ? false : showLineNumbers}
        >
          {source}
        </SyntaxHighlighter>
      )}
    </div>
  );
};

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
