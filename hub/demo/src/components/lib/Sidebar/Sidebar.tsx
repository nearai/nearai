'use client';

import { Button } from '@near-pagoda/ui';
import { X } from '@phosphor-icons/react';
import { type CSSProperties, type ReactNode } from 'react';

import { Footer } from '~/components/Footer';

import s from './Sidebar.module.scss';

export const Root = (props: { children: ReactNode }) => {
  return <div className={s.root} {...props} />;
};

export const Main = ({
  children,
  showFooter = true,
  style,
}: {
  children: ReactNode;
  showFooter?: boolean;
  style?: CSSProperties;
}) => {
  return (
    <div className={s.main}>
      <div className={s.mainContent} style={style}>
        {children}
      </div>
      {showFooter && <Footer />}
    </div>
  );
};

export const MainStickyFooter = ({ children }: { children: ReactNode }) => {
  return <div className={s.mainStickyFooter}>{children}</div>;
};

type SidebarProps = {
  children: ReactNode;
  openForSmallScreens: boolean;
  setOpenForSmallScreens: (open: boolean) => unknown;
  width?: string;
};

export const Sidebar = ({
  children,
  openForSmallScreens,
  setOpenForSmallScreens,
  width,
}: SidebarProps) => {
  return (
    <div className={s.sidebar} data-open-small-screens={openForSmallScreens}>
      <div className={s.sidebarContent} style={{ width, minWidth: width }}>
        <div className={s.sidebarContentInner}>
          <Button
            label="Close"
            icon={<X weight="bold" />}
            onClick={() => setOpenForSmallScreens(false)}
            className={s.sidebarCloseButton}
            fill="ghost"
            size="x-small"
          />

          {children}
        </div>
      </div>
    </div>
  );
};

export const SidebarContentBleed = ({ children }: { children: ReactNode }) => {
  return <div className={s.sidebarContentBleed}>{children}</div>;
};
