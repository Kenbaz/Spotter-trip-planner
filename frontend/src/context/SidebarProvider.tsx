import { useState } from "react";
import type { ReactNode } from "react";
import { SidebarContext } from "./SidebarContext";

export function SidebarProvider({ children }: { children: ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const setSidebarOpen = (open: boolean) => {
    setIsSidebarOpen(open);
  };

  const toggleSidebar = () => {
    setIsSidebarOpen((prev) => !prev);
  };

  return (
    <SidebarContext.Provider
      value={{ isSidebarOpen, setSidebarOpen, toggleSidebar }}
    >
      {children}
    </SidebarContext.Provider>
  );
}
