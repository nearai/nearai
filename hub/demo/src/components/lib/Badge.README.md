# Badge

```tsx
import { Badge } from '~/components/lib/Badge';

...

<Badge iconLeft={<Horse fill="bold" />} label="My Badge" />
<Badge label="My Badge" variant="neutral" />
<Badge label="My Badge" variant="alert" />
<Badge label="My Badge" variant="success" />
```

For displaying a number with fully rounded corners and bold font, apply the `count` prop:

```tsx
<Badge label="23" count />
```

## Chip (Clickable Badge)

Badges will typically be a readonly element. However, there are times where it can make sense to make them clickable. Simply add an `onClick` handler and `hover/focus` styles will automatically be applied (and the borders will be fully rounded):

```tsx
<Badge label="Click Me" onClick={() => { ... }} />
```
