import { createContext, useContext } from "react";

/** Live keyboard state, provided by MobileShell. `height` is the on-screen
 *  keyboard's pixel height (0 when closed) so fields can dock above it. */
export const KeyboardContext = createContext<{ open: boolean; height: number }>({
  open: false,
  height: 0,
});

export const useKeyboard = () => useContext(KeyboardContext);
