'use client';

import { X } from '@phosphor-icons/react';
import * as Primitive from '@radix-ui/react-dialog';
import type { ComponentProps, ReactNode } from 'react';
import { forwardRef } from 'react';

import { Button } from '../Button';
import s from './Dialog.module.scss';

export const Root = Primitive.Root;
export const Trigger = Primitive.Trigger;
export const Title = Primitive.Title;

type ContentProps = Omit<ComponentProps<typeof Primitive.Content>, 'title'> & {
  size?: 's' | 'm' | 'l';
  title?: ReactNode;
};

export const Content = forwardRef<HTMLDivElement, ContentProps>(
  ({ children, size = 'm', title, ...props }, ref) => {
    return (
      <Primitive.Portal>
        <Primitive.Overlay className={s.overlay}>
          <Primitive.Content
            className={s.content}
            data-size={size}
            ref={ref}
            {...props}
            onSubmit={(event) => {
              /*
              This prevents forms on the parent page from being submitted when a form
              inside the dialog is submitted:
            */
              event.stopPropagation();
            }}
          >
            <div className={s.header}>
              {title && (
                <Primitive.Title className={s.title}>{title}</Primitive.Title>
              )}

              <Primitive.Close asChild>
                <Button
                  className={s.close}
                  label="Close"
                  size="small"
                  variant="secondary"
                  fill="ghost"
                  icon={<X weight="bold" />}
                />
              </Primitive.Close>
            </div>

            <div className={s.body}>{children}</div>
          </Primitive.Content>
        </Primitive.Overlay>
      </Primitive.Portal>
    );
  },
);
Content.displayName = 'Content';
