import { cn } from "~/lib/utils";

export function One({ children }: { children: React.ReactNode }) {
  return (
    <h1 className="scroll-m-20 text-4xl font-extrabold tracking-tight lg:text-5xl">
      {children}
    </h1>
  );
}

export function Two({
  children,
  classname,
}: {
  classname?: string;
  children: React.ReactNode;
}) {
  return (
    <h2
      className={cn(
        "mt-10 scroll-m-20 pb-2 text-3xl font-semibold tracking-tight transition-colors first:mt-0",
        classname,
      )}
    >
      {children}
    </h2>
  );
}

export function Three({
  children,
  classname,
}: {
  children: React.ReactNode;
  classname?: string;
}) {
  return (
    <h3
      className={cn(
        "mt-10 pb-2 text-2xl font-semibold tracking-tight transition-colors first:mt-0",
        classname,
      )}
    >
      {children}
    </h3>
  );
}
