import { Card, Flex, SvgIcon, Text } from '@nearai/ui';
import { WarningCircle } from '@phosphor-icons/react';

type Props = {
  error: string;
};

export const ErrorMessage = ({ error }: Props) => {
  return (
    <Card border="red-10">
      <Flex align="center" gap="m">
        <SvgIcon icon={<WarningCircle />} color="red-10" />
        <Text>
          {error ||
            'We apologize for the unexpected interruption. Please try again later.'}
        </Text>
      </Flex>
    </Card>
  );
};
