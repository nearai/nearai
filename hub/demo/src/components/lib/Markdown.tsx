'use client';

import { Table } from '@nearai/ui';
import { memo } from 'react';
import ReactMarkdown, { defaultUrlTransform } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { visit } from 'unist-util-visit';

import { Code } from './Code';
import { InlineCode } from './InlineCode';
import s from './Markdown.module.scss';

type Props = {
  content: string | null | undefined;
};

type NodeMeta = Partial<{ codeLanguage: string }>;

function urlTransform(url: string) {
  if (url.startsWith('data:image/')) {
    return url;
  }
  return defaultUrlTransform(url);
}

export const Markdown = memo((props: Props) => {
  const content = props.content?.replace(/\s```/g, '\n```');

  return (
    <div className={s.markdown}>
      <ReactMarkdown
        remarkPlugins={[
          remarkGfm,
          () => (tree) => {
            visit(tree, 'code', (node: { meta?: NodeMeta; lang?: string }) => {
              node.meta = node.meta ?? {};
              node.meta.codeLanguage = node.lang ?? 'plaintext';
            });
          },
        ]}
        urlTransform={urlTransform}
        components={{
          code(props) {
            const { children, ...rest } = props;
            const meta = props.node?.data?.meta as NodeMeta | undefined;

            if (meta?.codeLanguage) {
              return (
                <Code
                  {...rest}
                  source={children as string}
                  language={meta?.codeLanguage}
                />
              );
            }

            return <InlineCode>{children}</InlineCode>;
          },

          table({ children, ...props }) {
            return <Table.Root {...props}>{children}</Table.Root>;
          },
          thead({ children, ...props }) {
            return <Table.Head {...props}>{children}</Table.Head>;
          },
          tbody({ children, ...props }) {
            return <Table.Body {...props}>{children}</Table.Body>;
          },
          tfoot({ children, ...props }) {
            return <Table.Foot {...props}>{children}</Table.Foot>;
          },
          th({ children, ...props }) {
            return <Table.HeadCell {...props}>{children}</Table.HeadCell>;
          },
          td({ children, ...props }) {
            return <Table.Cell {...props}>{children}</Table.Cell>;
          },
          tr({ children, ...props }) {
            return <Table.Row {...props}>{children}</Table.Row>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});

Markdown.displayName = 'Markdown';
