# Flex

This component helps solve common flex layout requirements. If you need a more sophisticated layout for your use case, consider creating a custom component with its own set of styles.

https://css-tricks.com/snippets/css/a-guide-to-flexbox/

```tsx
import { Flex } from '~/components/lib/Flex';
import { Text } from '~/components/lib/Text';

...

<Flex align="center" gap="m">
  <Text size="text-xl">Large</Text>
  <Text size="text-s">Small</Text>
</Flex>

<Flex justify="flex-end" gap="l">
  <Text>Item 1</Text>
  <Text>Item 2</Text>
</Flex>

<Flex direction="column" gap="xl" wrap="wrap">
  <Text>Item 1</Text>
  <Text>Item 2</Text>
</Flex>
```

## As

By default, `flex` renders a wrapping `<div>` tag. You can instead adjust it to be a `<label>` or `<span>` tag:

```tsx
<Flex as="label">
  <Text>Item 1</Text>
  <Text>Item 2</Text>
</Flex>

<Flex as="span">
  <Text>Item 1</Text>
  <Text>Item 2</Text>
</Flex>
```

## Breakpoint Adjustments

Sometimes you need to apply adjustments to the layout as the screen size gets smaller. You can do that by applying overrides for smaller screens with the `phone` and `tablet` props.

```tsx
<Flex
  align="center"
  gap="xl"
  tablet={{ align: 'flex-start', gap: 'l' }}
  phone={{ direction: 'column' }}
>
  <Text>Item 1</Text>
  <Text>Item 2</Text>
</Flex>
```
