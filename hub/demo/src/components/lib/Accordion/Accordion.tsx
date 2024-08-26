'use client';

import { CaretDown } from '@phosphor-icons/react';
import * as Primitive from '@radix-ui/react-accordion';
import type { ComponentProps } from 'react';
import { forwardRef } from 'react';

import { Flex } from '../Flex';
import s from './Accordion.module.scss';

type RootProps = ComponentProps<typeof Primitive.Root>;
type ContentProps = ComponentProps<typeof Primitive.Content>;
type TriggerProps = ComponentProps<typeof Primitive.Trigger>;
type ItemProps = ComponentProps<typeof Primitive.Item>;

export const Root = forwardRef<HTMLDivElement, RootProps>((props, ref) => {
  return <Primitive.Root className={s.root} ref={ref} {...props} />;
});
Root.displayName = 'Root';

export const Item = forwardRef<HTMLDivElement, ItemProps>((props, ref) => {
  return <Primitive.Item className={s.item} ref={ref} {...props} />;
});
Item.displayName = 'Item';

export const Trigger = forwardRef<HTMLButtonElement, TriggerProps>(
  ({ children, ...props }, ref) => {
    return (
      <Primitive.Header className={s.header}>
        <Primitive.Trigger className={s.trigger} ref={ref} {...props}>
          <Flex gap="m" align="center">
            {children}
          </Flex>
          <CaretDown weight="bold" className={s.indicator} />
        </Primitive.Trigger>
      </Primitive.Header>
    );
  },
);
Trigger.displayName = 'Trigger';

export const Content = forwardRef<HTMLDivElement, ContentProps>(
  ({ children, ...props }, ref) => {
    return (
      <Primitive.Content className={s.content} ref={ref} {...props}>
        <div className={s.contentContainer}>{children}</div>
      </Primitive.Content>
    );
  },
);
Content.displayName = 'Content';
