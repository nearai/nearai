# Tabs

Built with the Radix UI Tabs primitive: https://www.radix-ui.com/primitives/docs/components/tabs

## Links

This approach allows you to sync the active tab with the URL. This should be the preferred approach for most tabs.

```tsx
import { Tabs } from '~/components/lib/Tabs';
import { useRouter } from 'next/navigation';

...

const router = useRouter();
const selectedTab = router.query.tab as string;

...

<Tabs.Root value={selectedTab}>
  <Tabs.List>
    <Tabs.Trigger href="?tab=one" value="one">
      <SvgIcon icon={<Horse fill="bold" />} />
      Tab One
    </Tabs.Trigger>

    <Tabs.Trigger href="?tab=two" value="two">
      <SvgIcon icon={<Pizza fill="bold" />} />
      Tab Two
    </Tabs.Trigger>
  </Tabs.List>

  <Tabs.Content value="one">
    <Text>Content one.</Text>
  </Tabs.Content>

  <Tabs.Content value="two">
    <Text>Content two.</Text>
  </Tabs.Content>
</Tabs.Root>
```

## Buttons

```tsx
import { Tabs } from '~/components/lib';
...

<Tabs.Root>
  <Tabs.List>
    <Tabs.Trigger value="one">
      <SvgIcon icon={<Horse fill="bold" />} />
      Tab One
    </Tabs.Trigger>

    <Tabs.Trigger value="two">
      <SvgIcon icon={<Pizza fill="bold" />} />
      Tab Two
    </Tabs.Trigger>
  </Tabs.List>

  <Tabs.Content value="one">
    <Text>Content one.</Text>
  </Tabs.Content>

  <Tabs.Content value="two">
    <Text>Content two.</Text>
  </Tabs.Content>
</Tabs.Root>
```
