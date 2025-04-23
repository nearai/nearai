import express, { Request, Response } from "express";
import { McpServer, ToolCallback } from "@modelcontextprotocol/sdk/server/mcp.js"
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

import { JsonSchemaObject, jsonSchemaToZod } from "json-schema-to-zod";

import { z, ZodRawShape,  } from "zod";
import { CallToolRequest, TextContent } from "@modelcontextprotocol/sdk/types";

const app = express();
const PORT = 4000;

const server = new McpServer(
  {
    name: "dynamic-tools-server",
    version: "1.0.0"
  },
  {
    capabilities: {
      tools: {}
    }
  }
);

let transport: SSEServerTransport | null = null;

const settingsSchema = z.object({
  name: z.string(),
  command: z.string().optional(),
  args: z.array(z.string()).optional(),
  env: z.record(z.string()).optional(),
  url: z.string().optional(),
});

server.tool(
  "register_server",
  "Register a Nodejs MCP server within the MCP server proxy",
  {
    settings: settingsSchema,
  },
  async (params: { settings: z.infer<typeof settingsSchema> }) => {
    try {
      const { settings } = params;
      const { name, command, args, env, url } = settings;

      const connectionMethods = [
        { name: 'stdio', present: (command && args) || (command && env) || command },
        { name: 'sse', present: url }
      ].filter(m => m.present);

      if (connectionMethods.length !== 1) {
        throw new Error("Exactly one connection method ('stdio' or 'sse') must be provided");
      }

      const connectionMethod = connectionMethods[0].name;
      let transport: StdioClientTransport | SSEClientTransport | null = null;

      if (connectionMethod === 'stdio') {
        transport = new StdioClientTransport({ command: command || "", args: args || [], env: env || {} });
      } else {
        transport = new SSEClientTransport(new URL(url || ""));
      }

      const client = new Client(
        {
          name,
          version: "1.0.0"
        }
      );

      await client.connect(transport);

      const listToolsResponse = await client.listTools();
      listToolsResponse.tools.forEach(tool => {
        const zodSchema = jsonSchemaToZod(tool.inputSchema as JsonSchemaObject);
        const paramsSchema = eval(zodSchema) || {};
        const callTool = async (args: Record<string, any>) => {
          const result = await client.callTool({ name: tool.name, arguments: args }) as ReturnType<ToolCallback>;
          return result
        }
        server.tool(tool.name, tool.description || "", paramsSchema.shape, callTool);
      });

      return {
        content: [{
          type: "text",
          text: `MCP client ${name} registered successfully with ${connectionMethod} connection`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Error registering MCP client: ${(error as Error).message}`
        }],
        isError: true
      };
    }
  }
);


app.get("/sse", (req: Request, res: Response) => {
  transport = new SSEServerTransport("/messages", res);
  server.connect(transport);
});

app.post("/messages", (req: Request, res: Response) => {
  if (transport) {
    transport.handlePostMessage(req, res);
  }
});

app.listen(PORT, () => {
  console.log(`MCP Server running at http://localhost:${PORT}`);
  console.log(`SSE endpoint available at http://localhost:${PORT}/sse`);
  console.log(`Messages endpoint available at http://localhost:${PORT}/messages`);
});