import { type ReactNode } from 'react';

import s from './BreakpointDisplay.module.scss';

type Props = {
  children: ReactNode;
  className?: string;
  show:
    | 'sidebar-small-screen'
    | 'smaller-than-desktop'
    | 'smaller-than-tablet'
    | 'larger-than-phone'
    | 'larger-than-tablet';
};

export const BreakpointDisplay = ({
  children,
  className = '',
  show,
}: Props) => {
  return (
    <div className={`${s.breakpoint} ${className}`} data-show={show}>
      {children}
    </div>
  );
};
