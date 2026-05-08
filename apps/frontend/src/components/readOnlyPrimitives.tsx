import type { ReactNode } from 'react';

export function PlainPostText({ text }: { text: string }) {
  const parts = text.split(/(https?:\/\/\S+)/g);

  return (
    <p className="post-text">
      {parts.map((part, index) =>
        part.startsWith('http://') || part.startsWith('https://') ? (
          <span className="plain-url" key={`${part}-${index}`}>
            {part}
          </span>
        ) : (
          part
        ),
      )}
    </p>
  );
}

export function DisabledButton({
  children,
  className = 'muted-button',
}: {
  children: ReactNode;
  className?: string | undefined;
}) {
  return (
    <button className={className} type="button" disabled>
      {children}
    </button>
  );
}
