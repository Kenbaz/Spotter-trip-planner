import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Home,
  Route,
  Plus,
  User,
} from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { useSidebar } from "../../context/SidebarContext";
import { clsx } from "clsx";


const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: Home, end: true },
  { name: "My Trips", href: "/trips", icon: Route, end: true },
  { name: "New Trip", href: "/trips/new", icon: Plus, end: false },
  // { name: "Profile", href: "", icon: User, end: false },
];


export function Sidebar() {
  const { user } = useAuth();
  const { setSidebarOpen } = useSidebar();

  const closeNavWhenClicked = () => {
    setSidebarOpen(false);
  }


  const navItemVariants = {
    hover: {
      x: 4,
      transition: {
        type: "spring" as const,
        stiffness: 300,
        damping: 20,
      },
    },
    tap: {
      scale: 0.98,
    }
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        delayChildren: 0.1,
        staggerChildren: 0.05,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, x: -20 },
    visible: {
      opacity: 1,
      x: 0,
      transition: {
        type: "spring" as const,
        stiffness: 300,
        damping: 25,
      }
    },
  };

  return (
    <div className="w-64 md:w-full xl:w-[17rem] xl:mt-[24%] bg-[#FEFEFE] md:mt-[30%] border-r border-gray-200 overflow-y-auto h-full">
      <motion.div
        className="p-4"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Driver info */}
        <motion.div
          variants={itemVariants}
          className="mb-6 p-3 bg-blue-50 rounded-lg md:mt-[5%]"
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
              <User className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">
                {user?.full_name}
              </p>
              <p className="text-xs text-gray-500">{user?.role_display}</p>
              {user?.is_active_driver && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 mt-1">
                  <div className="w-1.5 h-1.5 bg-green-400 rounded-full mr-1"></div>
                  Active Driver
                </span>
              )}
            </div>
          </div>
        </motion.div>

        {/* Navigation */}
        <nav className="space-y-1">
          {navigation.map((item) => (
            <motion.div key={item.name} variants={itemVariants}>
              <NavLink
                to={item.href}
                end={item.end}
                onClick={closeNavWhenClicked}
                className={({ isActive }) =>
                  clsx(
                    "flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors",
                    isActive
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                  )
                }
              >
                {({ isActive }) => (
                  <motion.div
                    className={clsx(
                      "flex items-center w-full",
                      isActive ? "text-blue-700" : "text-gray-700"
                    )}
                    variants={navItemVariants}
                    whileHover="hover"
                    whileTap="tap"
                  >
                    <item.icon className="w-5 h-5 mr-3" />
                    {item.name}
                  </motion.div>
                )}
              </NavLink>
            </motion.div>
          ))}
        </nav>
      </motion.div>
    </div>
  );
};