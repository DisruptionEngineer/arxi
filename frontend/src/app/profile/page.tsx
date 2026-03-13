"use client";

import { useState } from "react";
import { useAuth } from "@/context/auth-context";
import { changePassword } from "@/lib/api";

const ROLE_COLORS: Record<string, string> = {
  admin: "bg-purple-900/40 text-purple-300",
  pharmacist: "bg-blue-900/40 text-blue-300",
  technician: "bg-green-900/40 text-green-300",
  agent: "bg-yellow-900/40 text-yellow-300",
};

export default function ProfilePage() {
  const { user } = useAuth();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!user) return null;

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);

    if (newPassword.length < 8) {
      setMessage({ type: "error", text: "New password must be at least 8 characters" });
      return;
    }
    if (newPassword !== confirmPassword) {
      setMessage({ type: "error", text: "Passwords do not match" });
      return;
    }

    setSubmitting(true);
    try {
      await changePassword(oldPassword, newPassword);
      setMessage({ type: "success", text: "Password changed successfully" });
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setMessage({ type: "error", text: err instanceof Error ? err.message : "Failed" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-semibold mb-6">Profile</h1>

      {/* User info */}
      <div className="bg-gray-900 rounded-lg p-6 mb-8">
        <div className="space-y-3">
          <div>
            <span className="text-sm text-gray-400">Full Name</span>
            <p className="text-white">{user.full_name}</p>
          </div>
          <div>
            <span className="text-sm text-gray-400">Username</span>
            <p className="text-white">{user.username}</p>
          </div>
          <div>
            <span className="text-sm text-gray-400">Role</span>
            <p>
              <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${ROLE_COLORS[user.role] || "bg-gray-800 text-gray-300"}`}>
                {user.role}
              </span>
            </p>
          </div>
        </div>
      </div>

      {/* Change password */}
      <h2 className="text-lg font-medium mb-4">Change Password</h2>
      <form onSubmit={handleChangePassword} className="space-y-4">
        {message && (
          <div className={`px-4 py-2 rounded-md text-sm border ${
            message.type === "success"
              ? "bg-green-900/30 border-green-700 text-green-300"
              : "bg-red-900/30 border-red-700 text-red-300"
          }`}>
            {message.text}
          </div>
        )}
        <div>
          <label className="block text-sm text-gray-400 mb-1">Current Password</label>
          <input type="password" value={oldPassword}
            onChange={(e) => setOldPassword(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white focus:outline-none focus:border-blue-500"
            required />
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-1">New Password</label>
          <input type="password" value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white focus:outline-none focus:border-blue-500"
            required minLength={8} />
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-1">Confirm New Password</label>
          <input type="password" value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-white focus:outline-none focus:border-blue-500"
            required minLength={8} />
        </div>
        <button type="submit" disabled={submitting}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50 transition-colors">
          {submitting ? "Changing..." : "Change Password"}
        </button>
      </form>
    </div>
  );
}
