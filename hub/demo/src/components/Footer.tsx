'use client';

import { Flex, Text } from '@nearai/ui';
import { useEffect, useState } from 'react';

import { APP_TITLE } from '@/constants';
import { useEmbeddedWithinIframe } from '@/hooks/embed';

import s from './Footer.module.scss';

type Props = {
  conditional?: boolean;
};

export const Footer = ({ conditional }: Props) => {
  const [mounted, setMounted] = useState(false);
  const { embedded } = useEmbeddedWithinIframe();

  useEffect(() => {
    if (!conditional && typeof window !== 'undefined') {
      const footer = document.querySelector(
        '[data-conditional-footer="true"]',
      ) as HTMLElement | null;
      if (!footer) return;
      footer.style.display = 'none';
      return () => {
        footer.style.display = '';
      };
    }
  }, [conditional]);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (embedded) return null;

  return (
    <footer
      className={s.footer}
      data-conditional-footer={conditional}
      data-hide={conditional && !mounted}
    >
      <Flex justify="space-between" gap="m" align="center" wrap="wrap">
        <Text size="text-xs">NEAR AI {APP_TITLE}</Text>

        <Flex wrap="wrap" gap="m">
          <Text
            href="https://near.ai"
            target="_blank"
            size="text-xs"
            color="sand-11"
          >
            NEAR AI
          </Text>

          <Text
            href="/terms-and-conditions.pdf"
            target="_blank"
            size="text-xs"
            color="sand-11"
          >
            Terms & Conditions
          </Text>
        </Flex>
      </Flex>
    </footer>
  );
};
