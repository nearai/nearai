# Dropdown

Built with the Radix UI Dropdown Menu primitive: https://www.radix-ui.com/primitives/docs/components/dropdown-menu

A more complex example when needing to implement sub dropdown menus:

```tsx
import { Horse, Pizza } from '@phosphor-icons/react';
import { Button, Dropdown, SvgIcon } from '~/components/lib/Dropdown';

...

<Dropdown.Root>
  <Dropdown.Trigger asChild>
    <Button label="My Dropdown" iconRight={<Dropdown.Indicator />} />
  </Dropdown.Trigger>

  <Dropdown.Content>
    <Dropdown.Section>
      <Dropdown.SectionContent>
        <Text size="text-xs" weight={600}>Section One</Text>
      </Dropdown.SectionContent>

      <Dropdown.Item>
        <SvgIcon icon={<Horse weight="fill" />} />
        Default Icon Color
      </Dropdown.Item>

      <Dropdown.Item>
        <SvgIcon icon={<Pizza weight="fill" />} color="red-9" />
        Custom Icon Color
      </Dropdown.Item>
    </Dropdown.Section>

    <Dropdown.Section>
      <Dropdown.SectionContent>
        <Text size="text-xs" weight={600}>Section One</Text>
      </Dropdown.SectionContent>

      <Dropdown.Item>Simple Item 1</Dropdown.Item>
      <Dropdown.Item>Simple Item 2</Dropdown.Item>

      <Dropdown.Sub>
        <Dropdown.SubTrigger asChild>
          <Dropdown.Item>Sub Menu Item</Dropdown.Item>
        </Dropdown.SubTrigger>

        <Dropdown.SubContent>
          <Dropdown.Item>Sub Item A</Dropdown.Item>
          <Dropdown.Item>Sub Item B</Dropdown.Item>
        </Dropdown.SubContent>
      </Dropdown.Sub>
    </Dropdown.Section>
  </Dropdown.Content>
</Dropdown.Root>
```
