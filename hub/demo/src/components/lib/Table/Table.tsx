'use client';

import { CaretCircleDown, CaretCircleUp } from '@phosphor-icons/react';
import Link from 'next/link';
import type {
  ComponentPropsWithRef,
  HTMLAttributeAnchorTarget,
  KeyboardEventHandler,
  ReactNode,
} from 'react';
import { forwardRef } from 'react';

import { Flex } from '../Flex';
import { Placeholder } from '../Placeholder';
import { SvgIcon } from '../SvgIcon';
import s from './Table.module.scss';

type RootProps = ComponentPropsWithRef<'table'>;

type HeadProps = ComponentPropsWithRef<'thead'> & {
  header?: ReactNode;
  sticky?: boolean;
};

type BodyProps = ComponentPropsWithRef<'tbody'>;

type FootProps = ComponentPropsWithRef<'tfoot'> & {
  sticky?: boolean;
};

type RowProps = ComponentPropsWithRef<'tr'>;

type HeadCellProps = ComponentPropsWithRef<'th'> & {
  sort?: 'ascending' | 'descending';
};

type CellProps = ComponentPropsWithRef<'td'> & {
  disabled?: boolean;
  href?: string;
  target?: HTMLAttributeAnchorTarget;
};

export const Root = forwardRef<HTMLTableElement, RootProps>(
  ({ children, ...props }, ref) => {
    return (
      <div className={s.root}>
        <table className={s.table} ref={ref} {...props}>
          {children}
        </table>
      </div>
    );
  },
);
Root.displayName = 'Root';

export const Head = forwardRef<HTMLTableSectionElement, HeadProps>(
  ({ children, header, sticky = true, ...props }, ref) => {
    return (
      <thead className={s.head} data-sticky={sticky} ref={ref} {...props}>
        {header && (
          <tr className={s.row}>
            <td className={s.headCustomCell} colSpan={10000}>
              {header}
            </td>
          </tr>
        )}

        {children}
      </thead>
    );
  },
);
Head.displayName = 'Head';

export const Body = forwardRef<HTMLTableSectionElement, BodyProps>(
  (props, ref) => {
    return <tbody className={s.body} ref={ref} {...props} />;
  },
);
Body.displayName = 'Body';

export const Foot = forwardRef<HTMLTableSectionElement, FootProps>(
  ({ sticky = true, ...props }, ref) => {
    return (
      <tfoot className={s.foot} data-sticky={sticky} ref={ref} {...props} />
    );
  },
);
Foot.displayName = 'Foot';

export const Row = forwardRef<HTMLTableRowElement, RowProps>((props, ref) => {
  const clickable = !!props.onClick;
  const role = clickable ? 'button' : undefined;
  const tabIndex = clickable ? 0 : undefined;

  const onKeyDown: KeyboardEventHandler<HTMLTableRowElement> = (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      event.stopPropagation();
      event.target.dispatchEvent(
        new Event('click', { bubbles: true, cancelable: true }),
      );
    }
    if (props.onKeyDown) props.onKeyDown(event);
  };

  return (
    <tr
      className={s.row}
      data-clickable={clickable}
      role={role}
      tabIndex={tabIndex}
      ref={ref}
      {...props}
      onKeyDown={onKeyDown}
    />
  );
});
Row.displayName = 'Row';

export const HeadCell = forwardRef<HTMLTableCellElement, HeadCellProps>(
  ({ children, sort, ...props }, ref) => {
    const clickable = !!props.onClick;
    const role = clickable ? 'button' : undefined;
    const tabIndex = clickable ? 0 : undefined;

    const onKeyDown: KeyboardEventHandler<HTMLTableCellElement> = (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        event.stopPropagation();
        event.target.dispatchEvent(
          new Event('click', { bubbles: true, cancelable: true }),
        );
      }
      if (props.onKeyDown) props.onKeyDown(event);
    };

    return (
      <th
        className={s.headCell}
        data-clickable={clickable}
        role={role}
        tabIndex={tabIndex}
        ref={ref}
        {...props}
        onKeyDown={onKeyDown}
      >
        <Flex align="center" as="span" gap="s">
          {children}
          {sort === 'descending' && (
            <SvgIcon icon={<CaretCircleDown weight="bold" />} size="xs" />
          )}
          {sort === 'ascending' && (
            <SvgIcon icon={<CaretCircleUp weight="bold" />} size="xs" />
          )}
        </Flex>
      </th>
    );
  },
);
HeadCell.displayName = 'HeadCell';

export const Cell = forwardRef<HTMLTableCellElement, CellProps>(
  ({ children, disabled, href, target, ...props }, ref) => {
    const clickable = !!props.onClick;
    const isButton = !!props.onClick && !href;
    const role = isButton ? 'button' : undefined;
    const tabIndex = isButton ? (disabled ? -1 : 0) : undefined;

    const onKeyDown: KeyboardEventHandler<HTMLTableCellElement> = (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        event.stopPropagation();
        event.target.dispatchEvent(
          new Event('click', { bubbles: true, cancelable: true }),
        );
      }
      if (props.onKeyDown) props.onKeyDown(event);
    };

    return (
      <td
        className={s.cell}
        aria-disabled={disabled}
        data-clickable={clickable}
        data-link={!!href}
        role={role}
        tabIndex={tabIndex}
        ref={ref}
        {...props}
        onKeyDown={onKeyDown}
      >
        {href ? (
          <Link href={href} className={s.cellAnchor} target={target}>
            {children}
          </Link>
        ) : (
          children
        )}
      </td>
    );
  },
);
Cell.displayName = 'Cell';

export const PlaceholderRows = () => {
  return (
    <>
      <tr className={s.row}>
        <td className={s.cell} colSpan={10000}>
          <Placeholder />
        </td>
      </tr>
      <tr className={s.row}>
        <td className={s.cell} colSpan={10000}>
          <Placeholder />
        </td>
      </tr>
      <tr className={s.row}>
        <td className={s.cell} colSpan={10000}>
          <Placeholder />
        </td>
      </tr>
    </>
  );
};
