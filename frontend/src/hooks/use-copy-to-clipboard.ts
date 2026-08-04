import { useState, useCallback } from "react";
import { toast } from "sonner";

export function useCopyToClipboard(timeout = 2000) {
  const [isCopied, setIsCopied] = useState(false);

  const copyToClipboard = useCallback(
    (text: string, successMessage = "Copied to clipboard") => {
      if (!text) return;
      if (typeof window === "undefined" || !navigator.clipboard) {
        toast.error("Clipboard not supported");
        return;
      }
      navigator.clipboard.writeText(text).then(() => {
        setIsCopied(true);
        toast.success(successMessage);
        setTimeout(() => {
          setIsCopied(false);
        }, timeout);
      });
    },
    [timeout]
  );

  return { isCopied, copyToClipboard };
}
