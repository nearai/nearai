# Grid

This component helps solve common grid layout requirements. If you need a more sophisticated layout for your use case, consider creating a custom component with its own set of styles.

https://css-tricks.com/snippets/css/complete-guide-grid/

```tsx
import { Grid } from '~/components/lib/Grid';
import { Card } from '~/components/lib/Card';

...

<Grid columns="1fr 1fr" gap="m">
  <Card>Card 1</Card>
  <Card>Card 2</Card>
  <Card>Card 3</Card>
  <Card>Card 4</Card>
</Grid>

<Grid columns="1fr 200px 2rem" align="center" justify="end" gap="xl">
  <Card>Card 1</Card>
  <Card>Card 2</Card>
  <Card>Card 3</Card>
  <Card>Card 4</Card>
  <Card>Card 5</Card>
</Grid>
```

## Breakpoint Adjustments

Sometimes you need to apply adjustments to the layout as the screen size gets smaller. You can do that by applying overrides for smaller screens with the `phone` and `tablet` props.

### Columns

Switch the defined `columns` when the screen is small enough to be considered a `tablet` or `phone`:

```tsx
<Grid
  columns="1fr 1fr 200px 100px"
  gap="xl"
  tablet={{ columns: '1fr 1fr', gap: 'l' }}
  phone={{ columns: '1fr' }}
>
  <Card>Card 1</Card>
  <Card>Card 2</Card>
  <Card>Card 3</Card>
  <Card>Card 4</Card>
</Grid>
```

## Width Overflow Issues

Sometimes you can end up having children inside your grid that want to expand to a point that would cause horizontal overflow. This can tend to happen more commonly when using `fr` units for a column. One option is to ignore the minimum size of the child by using the `minmax(0, 1fr)` syntax for the problematic column.

```tsx
<Grid columns="200px 1fr minmax(0, 1fr)" gap="m">
  <Card>Card 1</Card>
  <Card>Card 2</Card>
  <Card>Card 3 is really wide and wants to cause horizontal overflow</Card>
</Grid>
```

You can also look into using the `fit-content()` and `clamp()` grid properties.
