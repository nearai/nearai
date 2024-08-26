import type { CSSProperties, ReactNode } from 'react';

import s from './Pattern.module.scss';

type Props = {
  children: ReactNode;
  contentMaxWidth?: string;
  className?: string;
  style?: CSSProperties;
};

export const Pattern = ({
  className = '',
  children,
  contentMaxWidth,
  ...props
}: Props) => {
  return (
    <div className={`${s.pattern} ${className}`} {...props}>
      <div className={s.content} style={{ maxWidth: contentMaxWidth }}>
        {children}
      </div>
    </div>
  );
};
