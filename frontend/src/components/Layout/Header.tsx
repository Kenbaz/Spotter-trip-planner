import { Bell, User, LogOut, Menu } from "lucide-react";
import { motion } from "framer-motion";
import { useSidebar } from "../../context/SidebarContext";
import { useAuth } from "../../hooks/useAuth";
import { useState } from "react";
import { Link } from "react-router-dom";

export function Header() {
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const { toggleSidebar, isSidebarOpen } = useSidebar();

  const handleLogout = async () => {
    await logout();
    setShowUserMenu(false);
  };

  const menuButtonVariants = {
    open: {
      rotate: 90,
      scale: 1.1,
    },
    closed: {
      rotate: 0,
      scale: 1
    }
  };

  return (
    <header className="bg-[#FEFEFE] border-b border-gray-200 h-16 fixed top-0 left-0 right-0 z-50">
      <div className="flex items-center justify-between h-full px-6">
        {/* Left side - Mobile menu button and Logo */}
        <div className="flex items-center">
          {/* Mobile menu button */}
          <motion.button
            onClick={toggleSidebar}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg mr-3 md:hidden"
            aria-label="Toggle sidebar"
            variants={menuButtonVariants}
            animate={isSidebarOpen ? "open" : "closed"}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
            transition={{
              type: "spring",
              stiffness: 300,
              damping: 20,
            }}
          >
            <Menu className="w-5 h-5" />
          </motion.button>

          {/* Logo and app name */}
          <Link to="/">
            <div
              className="flex items-center space-x-3"
            >
              <div
                className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center"
              >
                <span className="text-white font-bold text-sm">S</span>
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">
                  Spotter HOS
                </h1>
                <p className="text-xs text-gray-500">Trip Planner</p>
              </div>
            </div>
          </Link>
        </div>

        {/* Right side, User info and actions */}
        <div className="flex items-center space-x-4">
          <motion.button
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
          >
            <Bell className="w-5 h-5" />
          </motion.button>

          {/* User menu */}
          <div className="relative">
            <motion.button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-100"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center">
                <User className="w-4 h-4 text-gray-600" />
              </div>
              <div className="text-left hidden sm:block">
                <p className="text-sm font-medium text-gray-900">
                  {user?.full_name}
                </p>
                <p className="text-xs text-gray-500">{user?.role_display}</p>
              </div>
            </motion.button>

            {/* Dropdown menu */}
            {showUserMenu && (
              <motion.div
                className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5"
                initial={{ opacity: 0, y: -10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -10, scale: 0.95 }}
                transition={{
                  type: "spring",
                  stiffness: 300,
                  damping: 25,
                  duration: 0.2,
                }}
              >
                <div className="py-1">
                  <div className="px-4 py-2 border-b border-gray-100">
                    <p className="text-sm font-medium text-gray-900">
                      {user?.full_name}
                    </p>
                    <p className="text-xs text-gray-500">{user?.username}</p>
                    <p className="text-xs text-gray-500">
                      ID: {user?.employee_id}
                    </p>
                  </div>

                  {/* <motion.button
                    onClick={() => setShowUserMenu(false)}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center"
                    whileHover={{ x: 4 }}
                    transition={{ type: "spring", stiffness: 400, damping: 20 }}
                  >
                    <User className="w-4 h-4 mr-2" />
                    Profile
                  </motion.button> */}

                  <motion.button
                    onClick={handleLogout}
                    className="w-full text-left px-4 py-2 text-sm text-red-700 hover:bg-red-50 flex items-center"
                    whileHover={{ x: 4 }}
                    transition={{ type: "spring", stiffness: 400, damping: 20 }}
                  >
                    <LogOut className="w-4 h-4 mr-2" />
                    Sign Out
                  </motion.button>
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
