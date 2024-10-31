import Link from 'next/link';
import { type ComponentPropsWithRef, forwardRef, type ReactNode } from 'react';

import { type ThemeColor } from '~/utils/theme';

import s from './Card.module.scss';

type Props = ComponentPropsWithRef<'div'> & {
  animateIn?: boolean;
  href?: string;
  target?: ComponentPropsWithRef<'a'>['target'];
  background?: ThemeColor;
  border?: ThemeColor;
  padding?: 's' | 'm' | 'l';
  paddingInline?: 's' | 'm' | 'l';
  gap?: 'xs' | 's' | 'm' | 'l';
};

export const Card = forwardRef<HTMLDivElement, Props>(
  (
    {
      animateIn,
      background = 'sand-0',
      border = 'sand-5',
      className = '',
      gap,
      padding,
      paddingInline,
      style,
      ...props
    },
    ref,
  ) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const Element: any = props.href ? Link : 'div';

    return (
      <Element
        className={`${s.card} ${className}`}
        data-animate-in={animateIn}
        data-background={background}
        data-gap={gap}
        data-padding={padding}
        data-padding-inline={paddingInline}
        role={props.onClick ? 'button' : undefined}
        tabIndex={(props.tabIndex ?? props.onClick) ? 0 : undefined}
        ref={ref}
        style={{
          '--card-background-color': `var(--${background})`,
          '--card-border-color': `var(--${border})`,
          ...style,
        }}
        {...props}
      />
    );
  },
);

Card.displayName = 'Card';

export const CardList = ({ children }: { children: ReactNode }) => {
  return <div className={s.cardList}>{children}</div>;
};

export const CardThumbnail = ({ alt, src }: { alt: string; src: string }) => {
  return (
    <div className={s.cardThumbnail}>
      <img alt={alt} src={src} />
    </div>
  );
};
