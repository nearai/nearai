'use client';

import { CaretDown } from '@phosphor-icons/react';
import * as Primitive from '@radix-ui/react-dropdown-menu';
import { useRouter } from 'next/navigation';
import type { ComponentProps, MouseEventHandler, ReactNode } from 'react';
import { forwardRef } from 'react';

import { SvgIcon } from '../SvgIcon';
import s from './Dropdown.module.scss';

export const Root = Primitive.Root;
export const Trigger = Primitive.Trigger;
export const Sub = Primitive.Sub;
export const SubTrigger = Primitive.SubTrigger;

export const Content = forwardRef<
  HTMLDivElement,
  ComponentProps<typeof Primitive.Content>
>(({ children, ...props }, ref) => {
  return (
    <Primitive.Portal>
      <Primitive.Content
        className={s.content}
        sideOffset={6}
        ref={ref}
        {...props}
      >
        <div className={s.scroll}>{children}</div>

        <Primitive.Arrow className={s.arrowBorder} />
        <Primitive.Arrow className={s.arrowFill} />
      </Primitive.Content>
    </Primitive.Portal>
  );
});
Content.displayName = 'Content';

export const SubContent = forwardRef<
  HTMLDivElement,
  ComponentProps<typeof Primitive.SubContent>
>(({ children, ...props }, ref) => {
  return (
    <Primitive.Portal>
      <Primitive.SubContent
        className={s.content}
        sideOffset={14}
        ref={ref}
        {...props}
      >
        <div className={s.scroll}>{children}</div>
      </Primitive.SubContent>
    </Primitive.Portal>
  );
});
SubContent.displayName = 'SubContent';

export const Item = forwardRef<
  HTMLDivElement,
  ComponentProps<typeof Primitive.Item> & { external?: boolean; href?: string }
>(({ external, href, ...props }, ref) => {
  const router = useRouter();

  const onClick: MouseEventHandler = (event) => {
    if (href) {
      if (event.metaKey || external) {
        window.open(href, '_blank');
      } else {
        void router.push(href);
      }
    }
  };

  return (
    <Primitive.Item className={s.item} ref={ref} {...props} onClick={onClick} />
  );
});
Item.displayName = 'Item';

export const Indicator = () => {
  return <SvgIcon icon={<CaretDown weight="bold" />} className={s.indicator} />;
};

export const Section = ({ children }: { children: ReactNode }) => {
  return <div className={s.section}>{children}</div>;
};

export const SectionContent = ({ children }: { children: ReactNode }) => {
  return <div className={s.sectionContent}>{children}</div>;
};
