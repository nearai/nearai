# Timestamp

This component uses `<NoSsr>` to prevent server side rendering of timestamps - which prevents hydration errors due to the server and client ending up with slightly different outputs.

```tsx
import { Text } from '~/components/lib/Text';
import { Timestamp } from '~/components/lib/Timestamp';

...

<Text>
  My cool date:
  <Timestamp date={new Date()} />
</Text>

```
