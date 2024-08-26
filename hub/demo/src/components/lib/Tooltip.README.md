# Tooltip

Built with the Radix UI Tooltip primitive: https://www.radix-ui.com/primitives/docs/components/tooltip

```tsx
import { Button } from '~/components/lib/Button';
import { Tooltip } from '~/components/lib/Tooltip';

...

<Tooltip content="Hello there!" asChild>
  <Button label="Click Me" />
</Tooltip>
```

If the element you're wrapping a tooltip around is a custom component that doesn't support ref forwarding, simply omit the `asChild` prop. This will result in Radix wrapping your trigger element with an unstyled `<button>` element. You'll also know you need to omit `asChild` if you see console errors when attempting to render your tooltip.
