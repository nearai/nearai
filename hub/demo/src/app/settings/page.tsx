'use client';

import { Gear } from '@phosphor-icons/react';

import { Flex } from '~/components/lib/Flex';
import { Section } from '~/components/lib/Section';
import { SvgIcon } from '~/components/lib/SvgIcon';
import { Text } from '~/components/lib/Text';

import { NonceList } from './NonceList';

export default function Settings() {
  return (
    <>
      <Section background="sand2">
        <Flex align="center" gap="m">
          <SvgIcon icon={<Gear weight="thin" />} size="l" />
          <Text as="h1">Settings</Text>
        </Flex>
      </Section>

      <Section>
        <NonceList />
      </Section>
    </>
  );
}
