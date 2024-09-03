# Text

```tsx
import { Text } from '~/components/lib/Text';

...

<Text>My Text</Text>
<Text color="violet-11" weight={600}>My Text</Text>
<Text size="text-xs">My Text</Text>
<Text as="h1">My Text</Text>
<Text as="h2" size="text-s" color="red-8">My Text</Text>
```

## Line Clamp

```tsx
<Text clampLines={2}>
  This is some super duper long text that will be clamped to two lines
  dynamically.
</Text>
```
