import { CheckCircle, WarningCircle } from '@phosphor-icons/react';

import { type ThemeInputVariant } from '~/utils/theme';

import { Flex } from './Flex';
import { SvgIcon } from './SvgIcon';
import { Text } from './Text';

type Props = {
  message?: string;
  variant: ThemeInputVariant;
  id?: string;
};

export const AssistiveText = ({ message, variant, id }: Props) => {
  if (!message) return null;

  if (variant === 'error') {
    return (
      <Flex gap="xs" align="center">
        <SvgIcon
          icon={<WarningCircle weight="bold" />}
          color="red8"
          size="xs"
        />
        <Text color="red11" size="text-xs" id={id}>
          {message}
        </Text>
      </Flex>
    );
  } else if (variant === 'success') {
    return (
      <Flex gap="xs" align="center">
        <SvgIcon
          icon={<CheckCircle weight="bold" />}
          color="green8"
          size="xs"
        />
        <Text color="green11" size="text-xs" id={id}>
          {message}
        </Text>
      </Flex>
    );
  } else {
    return (
      <Text color="sand11" size="text-xs" id={id}>
        {message}
      </Text>
    );
  }
};
