'use client';

import { X } from '@phosphor-icons/react';
import { type ReactNode, useEffect, useState } from 'react';

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
  const [footerOffset, setFooterOffset] = useState(0);
  const [animateFooterOffset, setAnimateFooterOffset] = useState(false);

  useEffect(() => {
    function onScroll() {
      const rect = document.getElementById('footer')!.getBoundingClientRect();
      const offset = Math.max(window.innerHeight - rect.top, 0);
      setFooterOffset(offset);
    }

    onScroll();

    setTimeout(() => {
      setAnimateFooterOffset(true);
    }, 250);

    window.addEventListener('scroll', onScroll);

    () => {
      window.removeEventListener('scroll', onScroll);
    };
  });

  return (
    <div className={s.sidebar} data-open-small-screens={openForSmallScreens}>
      <div
        className={s.content}
        style={{
          paddingTop: `${footerOffset}px`,
          transition: animateFooterOffset ? 'padding 200ms' : undefined,
        }}
      >
        <div className={s.contentInner}>
          <Button
            label="Close"
            icon={<X weight="bold" />}
            onClick={() => setOpenForSmallScreens(false)}
            className={s.closeButton}
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

export const Main = (props: { children: ReactNode }) => {
  return <div className={s.main} {...props} />;
};
