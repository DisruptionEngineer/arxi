"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/auth-context";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/queue", label: "Rx Queue" },
  { href: "/new-rx", label: "New Rx" },
  { href: "/ingest", label: "E-Prescribe" },
  { href: "/patients", label: "Patients" },
  { href: "/demo", label: "AI Demo" },
];

const ADMIN_NAV_ITEMS = [
  { href: "/audit", label: "Audit Trail" },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  return (
    <aside className="w-56 bg-gray-950 border-r border-gray-800 min-h-screen p-4 flex flex-col">
      <div className="text-sm uppercase text-gray-500 mb-4 tracking-wider">
        ARXI
      </div>
      <nav className="flex flex-col gap-1 flex-1">
        {NAV_ITEMS.map((item) => {
          const isActive = item.href === "/"
            ? pathname === "/"
            : pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`px-3 py-2 rounded-md text-sm ${
                isActive
                  ? "bg-blue-900/40 text-blue-300"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
        {user?.role === "admin" && ADMIN_NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`px-3 py-2 rounded-md text-sm ${
              pathname === item.href
                ? "bg-blue-900/40 text-blue-300"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      {/* User section at bottom */}
      {user && (
        <div className="border-t border-gray-800 pt-3 mt-3 space-y-1">
          <Link
            href="/profile"
            className={`block px-3 py-2 rounded-md text-sm ${
              pathname === "/profile"
                ? "bg-blue-900/40 text-blue-300"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
            }`}
          >
            <div className="font-medium text-gray-200 text-xs">{user.full_name}</div>
            <div className="text-xs text-gray-500">{user.role}</div>
          </Link>
          <button
            onClick={handleLogout}
            className="w-full text-left px-3 py-2 rounded-md text-sm text-gray-400 hover:text-red-300 hover:bg-gray-800"
          >
            Sign out
          </button>
        </div>
      )}
    </aside>
  );
}
