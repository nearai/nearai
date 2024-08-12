import { type z } from "zod";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "~/components/ui/card";
import { type oneModelModel } from "~/lib/models";

export default function ModelCard({
  model,
}: {
  model: z.infer<typeof oneModelModel>;
}) {
  console.log("model", model);
  const [provider, modelName] = model.id.split("::");

  return (
    <Card>
      <CardHeader>
        <CardTitle>{modelName}</CardTitle>
        <CardDescription>Provider: {provider}</CardDescription>
      </CardHeader>
      <CardContent>
        <p>Creation date: {new Date(model.created * 1000).toString()}</p>
        <p>Context length: {model.context_length ?? "N/A"}</p>
        <p>Supports chat: {model.supports_chat.toString()}</p>
        <p>Supports image input: {model.supports_image_input.toString()}</p>
        <p>Supports tools: {model.supports_tools.toString()}</p>
      </CardContent>
    </Card>
  );
}
