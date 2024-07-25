import { type z } from "zod";
import { type messageModel } from "~/lib/models";

function getBgColor(role: string) {
  switch (role) {
    case "user":
      return "bg-white w-fit text-right self-end";
    case "assistant":
      return "bg-green-200 w-fit";
    case "system":
      return "bg-yellow-200 w-fit";
    default:
      return "bg-gray-200 w-fit";
  }
}

export function ChatBubble(message: z.infer<typeof messageModel>) {
  return (
    <div
      className={`max-w-[80%] rounded-lg p-4 shadow ${getBgColor(message.role)}`}
    >
      <span>{message.content}</span>
    </div>
  );
}

export function Conversation(props: {
  messages: z.infer<typeof messageModel>[];
}) {
  const messages = props.messages;

  if (!messages.length) {
    return (
      <div>
        Welcome to NearAI Hub demo
        <ul>
          <li>
            Login with Near, write a prompt in the below text area, and click "Send" to see the
            chosen model response
          </li>
        </ul>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {messages.map((message, index) => (
        <ChatBubble key={index} {...message} />
      ))}
    </div>
  );
}
