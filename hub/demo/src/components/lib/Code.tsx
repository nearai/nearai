'use client';

import { useTheme } from '@nearai/ui';
import { Button, copyTextToClipboard, Tooltip } from '@nearai/ui';
import { Copy } from '@phosphor-icons/react';
import { memo, useEffect, useState } from 'react';
import SyntaxHighlighter from 'react-syntax-highlighter';
import {
  atomOneDark,
  atomOneLight,
} from 'react-syntax-highlighter/dist/esm/styles/hljs';

import s from './Code.module.scss';

export type CodeLanguage =
  | 'shell'
  | 'css'
  | 'html'
  | 'javascript'
  | 'typescript'
  | 'markdown'
  | 'python'
  | 'json'
  | (string & {})
  | undefined
  | null;

type Props = {
  bleed?: boolean;
  language: CodeLanguage;
  showCopyButton?: boolean;
  showLineNumbers?: boolean;
  source: string | undefined | null;
};

function normalizeLanguage(input: string | null | undefined) {
  if (!input) return '';

  let value: CodeLanguage = input;

  if (['js', 'jsx'].includes(value)) {
    value = 'javascript';
  } else if (['ts', 'tsx'].includes(value)) {
    value = 'typescript';
  } else if (value === 'py') {
    value = 'python';
  } else if (value === 'md') {
    value = 'markdown';
  }

  return value;
}

export const Code = memo(
  ({
    bleed,
    showCopyButton = true,
    showLineNumbers = true,
    ...props
  }: Props) => {
    const { resolvedTheme } = useTheme();
    const [mounted, setMounted] = useState(false);
    const language = normalizeLanguage(props.language);
    const source = props.source?.replace(/[\n]+$/, '').replace(/^[\n]+/, '');

    const style =
      mounted && resolvedTheme === 'dark' ? atomOneDark : atomOneLight;

    useEffect(() => {
      setMounted(true);
    }, []);

    if (!mounted) return null;

    return (
      <div
        className={s.code}
        data-bleed={bleed}
        data-copy={showCopyButton}
        data-language={language}
      >
        {showCopyButton && (
          <Tooltip asChild content="Copy to clipboard">
            <Button
              label="Copy code to clipboard"
              icon={<Copy />}
              variant="secondary"
              size="small"
              fill="ghost"
              onClick={() => source && copyTextToClipboard(source)}
              className={s.copyButton}
              tabIndex={-1}
            />
          </Tooltip>
        )}

        {source && (
          <SyntaxHighlighter
            PreTag="div"
            language={language ?? ''}
            style={style}
            showLineNumbers={showLineNumbers}
          >
            {source}
          </SyntaxHighlighter>
        )}
      </div>
    );
  },
);

Code.displayName = 'Code';
