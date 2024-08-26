'use client';

import * as Primitive from '@radix-ui/react-tooltip';
import type { ComponentProps, ReactElement, ReactNode } from 'react';

import s from './Tooltip.module.scss';

type RootProps = Omit<ComponentProps<typeof Primitive.Root>, 'children'>;
type ContentProps = Omit<ComponentProps<typeof Primitive.Content>, 'content'>;

type Props = ContentProps & {
  asChild?: boolean;
  children: ReactElement;
  content: ReactNode;
  disabled?: boolean;
  root?: RootProps;
};

export const Tooltip = ({
  asChild,
  children,
  content,
  disabled,
  root,
  side = 'top',
  sideOffset = 6,
  ...props
}: Props) => {
  const delayDuration = root?.delayDuration ?? 200;

  return (
    <Primitive.Provider>
      <Primitive.Root
        delayDuration={delayDuration}
        open={disabled ? false : undefined}
        {...root}
      >
        <Primitive.Trigger
          className={asChild ? undefined : s.trigger}
          asChild={asChild}
          type="button"
        >
          {children}
        </Primitive.Trigger>

        <Primitive.Portal>
          <Primitive.Content
            className={s.content}
            side={side}
            sideOffset={sideOffset}
            {...props}
          >
            {content}
            <Primitive.Arrow className={s.arrowBorder} />
            <Primitive.Arrow className={s.arrowFill} />
          </Primitive.Content>
        </Primitive.Portal>
      </Primitive.Root>
    </Primitive.Provider>
  );
};
