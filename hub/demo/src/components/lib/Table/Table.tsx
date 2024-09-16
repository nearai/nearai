'use client';

import { CaretCircleDown, CaretCircleUp } from '@phosphor-icons/react';
import Link from 'next/link';
import type {
  ComponentPropsWithRef,
  HTMLAttributeAnchorTarget,
  KeyboardEventHandler,
  MouseEventHandler,
  ReactNode,
} from 'react';
import { createContext, forwardRef, useContext } from 'react';

import { Flex } from '../Flex';
import { Placeholder } from '../Placeholder';
import { SvgIcon } from '../SvgIcon';
import { type SortableTable } from './hooks';
import s from './Table.module.scss';

type RootProps = {
  children: ReactNode;
  className?: string;
  sort?: SortableTable;
  setSort?: (value: SortableTable) => unknown;
};

const TableContext = createContext<RootProps | undefined>(undefined);

export const Root = forwardRef<HTMLTableElement, RootProps>((props, ref) => {
  return (
    <TableContext.Provider value={props}>
      <div className={`${s.root} ${props.className}`}>
        <table className={s.table} ref={ref}>
          {props.children}
        </table>
      </div>
    </TableContext.Provider>
  );
});
Root.displayName = 'Root';

type HeadProps = ComponentPropsWithRef<'thead'> & {
  header?: ReactNode;
  sticky?: boolean;
};

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

type BodyProps = ComponentPropsWithRef<'tbody'>;

export const Body = forwardRef<HTMLTableSectionElement, BodyProps>(
  (props, ref) => {
    return <tbody className={s.body} ref={ref} {...props} />;
  },
);
Body.displayName = 'Body';

type FootProps = ComponentPropsWithRef<'tfoot'> & {
  sticky?: boolean;
};

export const Foot = forwardRef<HTMLTableSectionElement, FootProps>(
  ({ sticky = true, ...props }, ref) => {
    return (
      <tfoot className={s.foot} data-sticky={sticky} ref={ref} {...props} />
    );
  },
);
Foot.displayName = 'Foot';

type RowProps = ComponentPropsWithRef<'tr'>;

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

type HeadCellProps = ComponentPropsWithRef<'th'> &
  (
    | {
        column?: string;
        sortable?: never;
      }
    | {
        column: string;
        sortable:
          | boolean
          | {
              startingOrder: SortableTable['order'];
            };
      }
  );

export const HeadCell = forwardRef<HTMLTableCellElement, HeadCellProps>(
  ({ children, column, sortable, ...props }, ref) => {
    const { sort, setSort } = useContext(TableContext)!;
    const clickable = !!props.onClick || !!sortable;
    const role = clickable ? 'button' : undefined;
    const tabIndex = clickable ? 0 : undefined;
    const columnHasActiveSort = sort?.column === column;

    const onKeyDown: KeyboardEventHandler<HTMLTableCellElement> = (event) => {
      if (props.onKeyDown) props.onKeyDown(event);

      if (event.key === 'Enter') {
        event.preventDefault();
        event.stopPropagation();
        event.target.dispatchEvent(
          new Event('click', { bubbles: true, cancelable: true }),
        );
      }
    };

    const onClick: MouseEventHandler<HTMLTableCellElement> = (event) => {
      if (props.onClick) props.onClick(event);

      if (!sortable || !column || !sort || !setSort) return;

      if (
        (columnHasActiveSort && sort.order === 'ASCENDING') ||
        (!columnHasActiveSort &&
          typeof sortable === 'object' &&
          sortable.startingOrder === 'DESCENDING')
      ) {
        setSort({
          column,
          order: 'DESCENDING',
        });
      } else {
        setSort({
          column,
          order: 'ASCENDING',
        });
      }
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
        onClick={onClick}
      >
        <Flex align="center" as="span" gap="s">
          {children}

          {columnHasActiveSort ? (
            <>
              {sort?.order === 'DESCENDING' && (
                <SvgIcon
                  icon={<CaretCircleDown weight="duotone" />}
                  size="xs"
                  color="violet-10"
                />
              )}
              {sort?.order === 'ASCENDING' && (
                <SvgIcon
                  icon={<CaretCircleUp weight="duotone" />}
                  size="xs"
                  color="violet-10"
                />
              )}
            </>
          ) : (
            <>{sortable && <SvgIcon icon={<CaretCircleDown />} size="xs" />}</>
          )}
        </Flex>
      </th>
    );
  },
);
HeadCell.displayName = 'HeadCell';

type CellProps = ComponentPropsWithRef<'td'> & {
  disabled?: boolean;
  href?: string;
  target?: HTMLAttributeAnchorTarget;
};

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
