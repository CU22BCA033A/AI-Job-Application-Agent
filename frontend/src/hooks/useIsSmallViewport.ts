import { useEffect, useState } from "react";

/** True below the breakpoint where the 3D hero simplifies to a static gradient. */
export function useIsSmallViewport(breakpointPx = 640): boolean {
  const [isSmall, setIsSmall] = useState(
    () => window.matchMedia(`(max-width: ${breakpointPx}px)`).matches,
  );

  useEffect(() => {
    const query = window.matchMedia(`(max-width: ${breakpointPx}px)`);
    const listener = (event: MediaQueryListEvent) => setIsSmall(event.matches);
    query.addEventListener("change", listener);
    return () => query.removeEventListener("change", listener);
  }, [breakpointPx]);

  return isSmall;
}
