# Toast

Built with the Radix UI Toast primitive: https://www.radix-ui.com/docs/primitives/components/toast

The `openToast()` API is made possible with Zustand: https://github.com/pmndrs/zustand

## Example

Using the `openToast` API allows you to easily open a toast from any context:

```tsx
import { openToast } from '~/components/lib/Toast';

...

<Button
  onClick={() =>
    openToast({
      type: 'error',
      title: 'Toast Title',
      description: 'This is a great toast description.',
    })
  }
>
  Open a Toast
</Button>
```

You can pass other options too:

```tsx
import { Pizza } from '@phosphor-icons/react';

<Button
  onClick={() =>
    openToast({
      type: 'success', // success | info | error
      title: 'Toast Title',
      description: 'This is a great toast description.',
      icon: Pizza,
      duration: 20000, // milliseconds (pass Infinity to disable auto close)
      action: () => {
        alert(1);
      },
      actionText: 'Do Action',
    })
  }
>
  With an Action + Icon
</Button>;
```

## Deduplicate

If you need to ensure only a single instance of a toast is ever displayed at once, you can deduplicate by passing a unique `id` key. If a toast with the passed `id` is currently open, a new toast will not be opened:

```tsx
<Button
  onClick={() =>
    openToast({
      id: 'my-unique-toast',
      title: 'Toast Title',
      description: 'This is a great toast description.',
    })
  }
>
  Deduplicated Toast
</Button>
```
