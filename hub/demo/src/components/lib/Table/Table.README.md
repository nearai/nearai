# Table

Tables are great for listing lots of data for users to easily scan. This component doesn't implement sorting or filtering - that will be up to you to implement based on your individual needs. Sometimes it might make sense to filter/sort via an API or filter/sort on the client.

## Example

```tsx
import { Table } from '~/components/lib/Table';

const tableRows = [
  {
    id: 1000,
    icon: <SvgIcon icon={<Rainbow />} />,
    name: 'Franky Frank',
    favoriteColor: 'Orange',
    token: 'afsa2423asdfj32afd323',
    address: '1234 Cool Ave, Denver, CO',
  },
  {
    id: 2000,
    icon: <SvgIcon icon={<Sun />} />,
    name: 'Bobby Bob',
    favoriteColor: 'Blue',
    token: 'hrgerg34243hr23j4fkhj',
    address: '3456 Super Amazing St, Richmond, VA',
  },
  {
    id: 3000,
    icon: <SvgIcon icon={<Moon />} />,
    name: 'Stevey Steve',
    favoriteColor: 'Green',
    token: 'j3kj43543543jl543454jk',
    address: '65465 Some Really Long Address, Some Really Cool City, CO',
  },
];

...

<Table.Root>
  <Table.Head>
    <Table.Row>
      <Table.HeadCell>ID</Table.HeadCell>
      <Table.HeadCell>Name</Table.HeadCell>
      <Table.HeadCell>Color</Table.HeadCell>
      <Table.HeadCell>Token</Table.HeadCell>
      <Table.HeadCell>Address</Table.HeadCell>
      <Table.HeadCell></Table.HeadCell>
    </Table.Row>
  </Table.Head>

  <Table.Body>
    {tableRows.map((row) => (
      <Table.Row key={row.id}>
        <Table.Cell>{row.id}</Table.Cell>

        <Table.Cell>
          <Flex align="center" gap="s">
            {row.icon}
            {row.name}
          </Flex>
        </Table.Cell>

        <Table.Cell>
          <Badge label={row.favoriteColor} />
        </Table.Cell>

        <Table.Cell>
          <Text size="text-s" style={{ minWidth: '5rem' }} clampLines={1}>
            {row.token}
          </Text>
        </Table.Cell>

        <Table.Cell style={{ minWidth: '15rem' }}>
          {row.address}
        </Table.Cell>

        <Table.Cell style={{ width: '1px' }}>
          <Flex>
            <Button label="Edit" icon={<Pencil />} size="small" />
            <Button label="Delete" icon={<Trash />} size="small" variant="destructive" />
          </Flex>
        </Table.Cell>
      </Table.Row>
    ))}
  </Table.Body>
</Table.Root>
```

## Cell Sizes

In the example above, note the use of the `style` prop on some of the `Cell` components. You can get creative with setting `width`, `maxWidth`, or `minWidth` on a cell or its contents (EG: a nested `Text` component). You can even combine the `clampLines` prop of `<Text>` to implement ellipsis text overflow.

If you have a cell that contains something like a `Button` and you'd like the cell width to match the `Button` width exactly, you can set the `Cell` width to something really small (EG: `1px`). Due to how `<td>` elements determine their width, this will give us the desired result:

```tsx
<Table.Cell style={{ width: '1px' }}>
  <Flex>
    <Button label="Edit" icon={<Pencil />} size="small" />
    <Button
      label="Delete"
      icon={<Trash />}
      size="small"
      variant="destructive"
    />
  </Flex>
</Table.Cell>
```

## Clickable Rows

Sometimes it makes sense for an entire table row to be clickable. You can pass an `onClick()` prop to `Row` - which will automatically apply hover/focus styles:

```tsx
<Table.Row onClick={() => alert('Table Row Click')} key={row.id}>
  <Table.Cell>{row.id}</Table.Cell>
  <Table.Cell>{row.name}</Table.Cell>
  <Table.Cell>{row.favoriteColor}</Table.Cell>
</Table.Row>
```

## Clickable Cells

Sometimes it makes sense for individual cells to be clickable. You can pass an `onClick()` and `disabled` props to a `Cell` - which will automatically apply hover/focus styles:

```tsx
<Table.Row key={row.id}>
  <Table.Cell onClick={() => alert('This will trigger')}>{row.id}</Table.Cell>

  <Table.Cell disabled onClick={() => alert('This will not trigger')}>
    {row.name}
  </Table.Cell>
</Table.Row>
```

## Clickable Rows + Some Clickable Cells

In rare cases, it might make sense to have an entire row be clickable, but maybe 1 or 2 cells be clickable individually as well:

```tsx
<Table.Row onClick={() => alert('Table Row Click')} key={row.id}>
  <Table.Cell
    onClick={(event) => {
      event.stopPropagation();
      alert('Table Cell Click');
    }}
  >
    {row.id} (Cell Click)
  </Table.Cell>
  <Table.Cell>{row.name} (Row Click)</Table.Cell>
  <Table.Cell>{row.favoriteColor} (Row Click)</Table.Cell>
</Table.Row>
```

Note the use of `event.stopPropagation()` on the `Cell` click handler. This prevents the parent `Row` click handler from also firing.

## Clickable Header Cells

Just like regular table cells, you can pass an `onClick()` prop to a `HeadCell` - which will automatically apply hover/focus styles:

```tsx
<Table.Head>
  <Table.Row>
    <Table.HeadCell onClick={() => { ... }}>Date</Table.HeadCell>
    <Table.HeadCell>Name</Table.HeadCell>
  </Table.Row>
</Table.Head>
```

## Sortable Header Cells

You can combine the `onClick()` and `sort` props on a `HeadCell` to implement UI for toggling sort order by column. You can implement the actual sorting logic on either the client or API side depending on your needs. The `sort` prop simply renders an arrow icon indicating the current sort direction to the user (as well as indicating that it can be interacted with).

```tsx
import { useState } from 'react';

type SortType = 'DATE_ASC' | 'DATE_DES' | 'NAME_ASC' | 'NAME_DES';

...

const [sort, setSort] = useState<SortType>('DATE_DES');
// Apply client side or server side (API) sorting based on "sort" value...

...

<Table.Head>
  <Table.Row>
    <Table.HeadCell
      sort={sort === 'DATE_DES' ? 'descending' : 'ascending'}
      onClick={() => setSort(sort === 'DATE_DES' ? 'DATE_ASC' : 'DATE_DES')}
    >
      Date
    </Table.HeadCell>
    <Table.HeadCell
      sort={sort === 'NAME_DES' ? 'descending' : 'ascending'}
      onClick={() => setSort(sort === 'NAME_DES' ? 'NAME_ASC' : 'NAME_DES')}>
      Name
    </Table.HeadCell>
  </Table.Row>
</Table.Head>
```

## Cell Link (Anchor)

The `clickable` examples above work great for `<button>` interactions. However, if you're needing to link the user to a different route, that should be accomplished with an `<a>` tag. You can achieve this using the `href` and `target` props on `Table.Cell`:

```tsx
<Table.Row key={row.id}>
  <Table.Cell href="/my-url">Internal Anchor cell</Table.Cell>
  <Table.Cell href="/my-url" target="_blank">
    External Anchor cell
  </Table.Cell>
  <Table.Cell>Read only cell</Table.Cell>
</Table.Row>
```

## Sticky Header

By default, the `Header` uses sticky positioning that accounts for our main floating header. Sometimes you might want to disable the sticky positioning:

```tsx
<Table.Head sticky={false}>...</Table.Head>
```

Sometimes you might need to adjust the `top` positioning if your page doesn't render our main header:

```tsx
<Table.Head style={{ top: 0 }}>...</Table.Head>
```

## Custom Header

You can include custom content in the header at the top of the table using the `header` prop on `Table.Head`:

```tsx
<Table.Root>
  <Table.Head
    header={
      <Flex align="center" gap="m">
        <FeatherIcon icon="sun" />
        <H5>My Cool Table</H5>
        <Button size="s" color="primaryBorder">
          <FeatherIcon icon="sliders" />
          Filter
        </Button>
      </Flex>
    }
  >
    ...
  </Table.Head>
  <Table.Body>...</Table.Body>
</Table.Root>
```

## Footer

You can use `Table.Foot` to create a sticky footer with more table data:

```tsx
<Table.Root>
  ...
  <Table.Foot>
    <Table.Row>
      <Table.Cell>Cell 2 Data</Table.Cell>
      <Table.Cell>Cell 1 Data</Table.Cell>
    </Table.Row>
  </Table.Foot>
</Table.Root>
```

Or you can use it to render custom content (EG: filter controls, pagination). You'll probably want to set `colSpan` on the `Table.Cell` to span the full width of the table:

```tsx
<Table.Root>
  ...
  <Table.Foot>
    <Table.Row>
      <Table.Cell colSpan={100}>
        <Flex align="center" justify="end" gap="m">
          <Text>My Cool Footer</Text>
          <Button label="Filter" size="small" />
        </Flex>
      </Table.Cell>
    </Table.Row>
  </Table.Foot>
</Table.Root>
```

You can disable the footer sticky scroll:

```tsx
<Table.Foot sticky={false}>...</Table.Foot>
```

## Placeholder Rows

When data is loading for your table, you can use the `PlaceholderRows` component to show a loading placeholder:

```tsx
<Table.Body>
  {!myTableData && <Table.PlaceholderRows />}
  ...
</Table.Body>
```
