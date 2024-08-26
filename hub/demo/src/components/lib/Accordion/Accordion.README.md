# Accordion

Built with the Radix UI Accordion primitive: https://www.radix-ui.com/primitives/docs/components/accordion

```tsx
import { Accordion } from '~/components/lib/Accordion';

...

<Accordion.Root type="multiple">
  <Accordion.Item value="one">
    <Accordion.Trigger>First Section</Accordion.Trigger>

    <Accordion.Content>
      <Text>Content 1</Text>
      <Text>Content 1</Text>
      <Text>Content 1</Text>
    </Accordion.Content>
  </Accordion.Item>

  <Accordion.Item value="two">
    <Accordion.Trigger>Second Section</Accordion.Trigger>

    <Accordion.Content>
      <Text>Content 2</Text>
      <Text>Content 2</Text>
    </Accordion.Content>
  </Accordion.Item>
</Accordion.Root>
```
