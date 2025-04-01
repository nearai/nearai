import { Button, Container, Flex, Section, Text } from '@nearai/ui';
import { ArrowRight } from '@phosphor-icons/react';

type Props = {
  error: '404' | 'unknown';
};

export const ErrorSection = ({ error }: Props) => {
  let title = 'Unknown Error';
  let description =
    'We apologize for the unexpected interruption. Please try again later.';

  switch (error) {
    case '404':
      title = 'Not Found';
      description = `The page or resource you're looking for no longer exists.`;
      break;
  }

  return (
    <Section grow="available">
      <Container size="s" style={{ margin: 'auto', textAlign: 'center' }}>
        <Flex direction="column" gap="l" align="center">
          <Text as="h1" color="red-10">
            {title}
          </Text>
          <Text>{description}</Text>
          <Button href="/" label="Go Home" iconRight={<ArrowRight />} />
        </Flex>
      </Container>
    </Section>
  );
};
