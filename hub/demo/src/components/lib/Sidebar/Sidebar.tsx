'use client';

import { SvgIcon } from '@nearai/ui';
import { CaretDown } from '@phosphor-icons/react';
import { type CSSProperties, type ReactNode, useEffect, useRef } from 'react';

import { Footer } from '@/components/Footer';

import s from './Sidebar.module.scss';

export const Root = (props: { children: ReactNode }) => {
  const elementRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    function calculateSize() {
      if (!element) return;
      const rect = element.getBoundingClientRect();
      const top = Math.max(0, rect.top);
      element.style.setProperty(`--sidebar-root-top`, `${top}px`);
    }

    const resizeObserver = new ResizeObserver(() => {
      calculateSize();
    });

    calculateSize();
    resizeObserver.observe(element);
    window.addEventListener('scroll', calculateSize);

    () => {
      resizeObserver.disconnect();
      window.removeEventListener('scroll', calculateSize);
    };
  }, []);

  return <div className={s.root} ref={elementRef} {...props} />;
};

export const Main = ({
  children,
  fileDragIsActive,
  showFooter = true,
  style,
}: {
  children: ReactNode;
  fileDragIsActive?: boolean;
  showFooter?: boolean;
  style?: CSSProperties;
}) => {
  return (
    <div className={s.main} data-file-drag-is-active={fileDragIsActive}>
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
};

export const Sidebar = ({
  children,
  openForSmallScreens,
  setOpenForSmallScreens,
}: SidebarProps) => {
  return (
    <div className={s.sidebar} data-open-small-screens={openForSmallScreens}>
      <div className={s.sidebarContent}>
        <button
          type="button"
          onPointerDownCapture={(event) => {
            event.stopPropagation();
            setOpenForSmallScreens(false);
          }}
          onPointerUpCapture={(event) => {
            event.stopPropagation();
          }}
          onClickCapture={(event) => {
            event.stopPropagation();
          }}
          className={s.sidebarCloseButton}
        >
          <SvgIcon icon={<CaretDown weight="bold" />} size="s" />
        </button>

        <div className={s.sidebarContentInner}>{children}</div>
      </div>
    </div>
  );
};

export const SidebarContentBleed = ({ children }: { children: ReactNode }) => {
  return <div className={s.sidebarContentBleed}>{children}</div>;
};
