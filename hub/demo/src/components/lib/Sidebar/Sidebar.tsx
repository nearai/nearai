'use client';

import { X } from '@phosphor-icons/react';
import { type ReactNode } from 'react';

import { Footer } from '~/components/Footer';

import { Button } from '../Button';
import s from './Sidebar.module.scss';

type Props = {
  children: ReactNode;
  openForSmallScreens: boolean;
  setOpenForSmallScreens: (open: boolean) => unknown;
};

export const Sidebar = ({
  children,
  openForSmallScreens,
  setOpenForSmallScreens,
}: Props) => {
  return (
    <div className={s.sidebar} data-open-small-screens={openForSmallScreens}>
      <div className={s.sidebarContent}>
        <div className={s.sidebarContentInner}>
          <Button
            label="Close"
            icon={<X weight="bold" />}
            onClick={() => setOpenForSmallScreens(false)}
            className={s.sidebarCloseButton}
            size="small"
            fill="ghost"
          />

          {children}
        </div>
      </div>
    </div>
  );
};

export const Root = (props: { children: ReactNode }) => {
  return <div className={s.root} {...props} />;
};

export const Main = ({ children }: { children: ReactNode }) => {
  return (
    <div className={s.main}>
      {children}
      <Footer />
    </div>
  );
};
