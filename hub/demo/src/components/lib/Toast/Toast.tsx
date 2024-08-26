'use client';

import { X } from '@phosphor-icons/react';
import * as Primitive from '@radix-ui/react-toast';
import type { ComponentProps, ReactElement } from 'react';
import { forwardRef } from 'react';

import { Button } from '../Button';
import { SvgIcon } from '../SvgIcon';
import { type ToastType } from './store';
import s from './Toast.module.scss';

type ViewportProps = ComponentProps<typeof Primitive.Viewport>;
type RootProps = Omit<ComponentProps<typeof Primitive.Root>, 'type'> & {
  type: ToastType;
};
type TitleProps = ComponentProps<typeof Primitive.Title>;
type DescriptionProps = ComponentProps<typeof Primitive.Description>;

export const Action = Primitive.Action;
export const Provider = Primitive.Provider;

export const Viewport = forwardRef<HTMLOListElement, ViewportProps>(
  (props, ref) => {
    return <Primitive.Viewport className={s.viewport} ref={ref} {...props} />;
  },
);
Viewport.displayName = 'Viewport';

export const Root = forwardRef<HTMLLIElement, RootProps>(
  ({ type, ...props }, ref) => {
    return (
      <Primitive.Root
        className={s.root}
        data-type={type}
        ref={ref}
        {...props}
      />
    );
  },
);
Root.displayName = 'Root';

export const Title = forwardRef<HTMLDivElement, TitleProps>((props, ref) => {
  return <Primitive.Title className={s.title} ref={ref} {...props} />;
});
Title.displayName = 'Title';

export const Description = forwardRef<HTMLDivElement, DescriptionProps>(
  (props, ref) => {
    return (
      <Primitive.Description className={s.description} ref={ref} {...props} />
    );
  },
);
Description.displayName = 'Description';

export const Close = () => {
  return (
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
  );
};

export const Icon = ({ icon }: { icon: ReactElement }) => {
  return <SvgIcon className={s.icon} icon={icon} />;
};
