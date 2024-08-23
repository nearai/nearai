import './tabsStyle.css'

import * as Tabs from '@radix-ui/react-tabs';

const SimpleTabs = ({tabs, content}) => {
  return (
    <Tabs.Root className="TabsRoot" defaultValue="tab0">
      <Tabs.List className="TabsList">
        {Object.keys(tabs).map((tab, index) => (
          <Tabs.Trigger className="TabsTrigger" value={"tab"+index} key={"tab"+index}>
            {tab}
          </Tabs.Trigger>
        ))}
      </Tabs.List>
      {Object.keys(tabs).map((tab, index) => (
        <Tabs.Content className="TabsContent" value={"tab"+index} key={"tabContent"+index}>
          {content[tab]}
        </Tabs.Content>
      ))}

    </Tabs.Root>
  );
}

export default SimpleTabs;