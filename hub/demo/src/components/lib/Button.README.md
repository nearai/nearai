# Button

```tsx
import { Button } from '~/components/lib/Button';
import { Horse, Pizza } from '@phosphor-icons/react';

...

<Button label="Click Me" />

<Button label="Click Me" iconLeft={<Pizza fill="bold" />} />
<Button label="Click Me" iconRight={<Horse fill="bold" />} />
<Button label="Click Me" icon={<Horse fill="bold" />} />

<Button label="Click Me" color="affirmative" />
<Button label="Click Me" size="small" />
<Button label="Click Me" size="large" />
<Button label="Click Me" fill="outline" />
<Button label="Click Me" fill="ghost" />

<Button label="Click Me" loading />
<Button label="Click Me" disabled />

<Button label="Click Me" href="/foo/bar" />
<Button label="Click Me" href="/foo/bar" target="_blank" />
```
