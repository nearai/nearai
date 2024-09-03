# Card

```tsx
import { Card } from '~/components/lib/Card';

...

<Card>
  <Text>Some content</Text>
  <Text>And more content</Text>
</Card>
```

## Clickable Card

Cards will typically be a readonly element. However, there are times where it can make sense to make the entire card clickable. Simply add an `onClick` handler and `hover/focus` styles will automatically be applied (and the borders will be fully rounded):

```tsx
<Card aria-label="My Cool Card" onClick={() => { ... }}>
  <SvgIcon icon={<CalendarDots weight="duotone" />} size="m" color="violet-10" />
  <Text size="text-l">My Cool Card</Text>
  <Text>Some other content goes here.</Text>
</Card>
```
