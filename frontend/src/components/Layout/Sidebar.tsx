import { NavLink } from "react-router-dom";
import {
  Home,
  Route,
  Plus,
  User,
  MapPin,
} from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { clsx } from "clsx";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: Home },
  { name: "My Trips", href: "/trips", icon: Route },
  { name: "New Trip", href: "/trips/new", icon: Plus },
  { name: "Profile", href: "/profile", icon: User },
];

export function Sidebar() {
  const { user } = useAuth();

  return (
    <div className="fixed left-0 top-16 bottom-0 w-64 bg-white border-r border-gray-200 overflow-y-auto">
      <div className="p-4">
        {/* Driver info */}
        <div className="mb-6 p-3 bg-blue-50 rounded-lg">
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
        </div>

        {/* Navigation */}
        <nav className="space-y-1">
          {navigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) =>
                clsx(
                  "flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors",
                  isActive
                    ? "bg-blue-100 text-blue-700"
                    : "text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                )
              }
            >
              <item.icon className="w-5 h-5 mr-3" />
              {item.name}
            </NavLink>
          ))}
        </nav>

        {/* Vehicle assignment info */}
        <div className="mt-6 p-3 bg-gray-50 rounded-lg">
          <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
            Current Vehicle
          </h4>
          <div className="flex items-center space-x-2">
            <MapPin className="w-4 h-4 text-gray-400" />
            <div>
              <p className="text-sm font-medium text-gray-900">Unit-001</p>
              <p className="text-xs text-gray-500">2023 Freightliner</p>
            </div>
          </div>
        </div>

        {/* Quick stats */}
        <div className="mt-6 space-y-3">
          <div className="p-3 bg-green-50 rounded-lg">
            <p className="text-xs font-medium text-green-800">Today's Status</p>
            <p className="text-sm text-green-700">HOS Compliant</p>
          </div>

          <div className="p-3 bg-yellow-50 rounded-lg">
            <p className="text-xs font-medium text-yellow-800">Driving Hours</p>
            <p className="text-sm text-yellow-700">3.5 / 11 hours</p>
          </div>
        </div>
      </div>
    </div>
  );
}
