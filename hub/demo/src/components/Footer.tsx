import Link from 'next/link';

import s from './Footer.module.scss';
import { Flex } from './lib/Flex';
import { Text } from './lib/Text';

export const Footer = () => {
  return (
    <footer className={s.footer} id="footer">
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
