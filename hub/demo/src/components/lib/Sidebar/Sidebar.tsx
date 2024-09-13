'use client';

import { X } from '@phosphor-icons/react';
import { type ReactNode } from 'react';

import { Footer } from '~/components/Footer';

import { Button } from '../Button';
import s from './Sidebar.module.scss';

export const Root = (props: { children: ReactNode }) => {
  return <div className={s.root} {...props} />;
};

export const Main = ({ children }: { children: ReactNode }) => {
  return (
    <div className={s.main}>
      <div className={s.mainContent}>{children}</div>
      <Footer />
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
