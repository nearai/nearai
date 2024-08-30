'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import s from './Footer.module.scss';
import { Flex } from './lib/Flex';
import { Text } from './lib/Text';

type Props = {
  conditional?: boolean;
};

export const Footer = ({ conditional }: Props) => {
  const [mounted, setMounted] = useState(false);

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

  return (
    <footer
      className={s.footer}
      data-conditional-footer={conditional}
      data-hide={conditional && !mounted}
    >
      <Flex justify="space-between" gap="m" align="center" wrap="wrap">
        <Text size="text-xs">NEAR AI Hub</Text>

        <Flex wrap="wrap" gap="m">
          <Link href="https://near.ai" target="_blank">
            <Text size="text-xs" decoration="underline">
              near.ai
            </Text>
          </Link>

          <Link href="/terms-and-conditions.pdf" target="_blank">
            <Text size="text-xs" decoration="underline">
              Terms & Conditions
            </Text>
          </Link>
        </Flex>
      </Flex>
    </footer>
  );
};
