# Code

This component wraps [React Syntax Highlighter](https://react-syntax-highlighter.github.io/react-syntax-highlighter/demo/).

```tsx
import { Code } from '@/components/lib/Code';

...

<Code language="javascript" source={`() => alert('hi!')`}>
```

View the demo link above to see all supported `language` values.

## Line Numbers

By default, line numbers will be rendered. You can disable rendering line numbers by passing `showLineNumbers={false}`.
