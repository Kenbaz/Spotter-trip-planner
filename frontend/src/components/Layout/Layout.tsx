import type { ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { useSidebar } from "../../context/SidebarContext";

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { isSidebarOpen, setSidebarOpen } = useSidebar();
  
  const handleClickOutside = () => {
    setSidebarOpen(false);
  };

  const sidebarVariants = {
    open: {
      x: 0,
      transition: {
        type: "spring" as const,
        stiffness: 300,
        damping: 30,
      },
    },
    closed: {
      x: "-100%",
      transition: {
        type: "spring" as const,
        stiffness: 300,
        damping: 30,
      },
    },
  };


  const backdropVariants = {
    open: {
      opacity: 1,
      transition: {
        duration: 0.2,
      },
    },
    closed: {
      opacity: 0,
      transition: {
        duration: 0.2,
      },
    },
  }


  return (
    <div className="min-h-screen md:overflow-hidden bg-[#FAFAFA]">
      <Header />
      
      <div className="flex">
        {/* Desktop Sidebar */}
        <div className="hidden md:block">
          <Sidebar />
        </div>

        {/* Mobile Sidebar Backdrop */}
        <AnimatePresence>
          {isSidebarOpen && (
            <motion.div
              className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
              variants={backdropVariants}
              initial="closed"
              animate="open"
              exit="closed"
              onClick={handleClickOutside}
            />
          )}
        </AnimatePresence>

        {/* Mobile Sidebar */}
        <motion.div
          className="fixed top-16 left-0 bottom-0 z-50 md:hidden"
          variants={sidebarVariants}
          initial="closed"
          animate={isSidebarOpen ? "open" : "closed"}
        >
          <Sidebar />
        </motion.div>

        <main className="flex-1 md:mt-[7%] lg:mt-[5%] xl:pr-[2%] 2xl:pt-[1.3%] 2xl:mt-[3%] overflow-y-auto h-screen md:ml-[2%] p-[0.6rem] md:pb-[10%] main">
          {children}
        </main>
      </div>
    </div>
  );
}
