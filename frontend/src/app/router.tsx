import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { AppLayout } from "@/app/AppLayout";
import { ProtectedRoute } from "@/app/ProtectedRoute";
import { AccountingPage } from "@/features/accounting/AccountingPage";
import { AuditPage } from "@/features/audit/AuditPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { GroupsPage } from "@/features/groups/GroupsPage";
import { NasPage } from "@/features/nas/NasPage";
import { PostAuthPage } from "@/features/postauth/PostAuthPage";
import { SessionsPage } from "@/features/sessions/SessionsPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { ProfilesPage } from "@/features/shaping/ProfilesPage";
import { UserDetailPage } from "@/features/users/UserDetailPage";
import { UsersPage } from "@/features/users/UsersPage";

const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: "/", element: <DashboardPage /> },
          { path: "/users", element: <UsersPage /> },
          { path: "/users/:username", element: <UserDetailPage /> },
          { path: "/groups", element: <GroupsPage /> },
          { path: "/profiles", element: <ProfilesPage /> },
          { path: "/nas", element: <NasPage /> },
          { path: "/sessions", element: <SessionsPage /> },
          { path: "/accounting", element: <AccountingPage /> },
          { path: "/postauth", element: <PostAuthPage /> },
          { path: "/audit", element: <AuditPage /> },
          { path: "/settings", element: <SettingsPage /> },
        ],
      },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
