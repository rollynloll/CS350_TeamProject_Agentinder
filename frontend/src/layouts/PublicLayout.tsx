import { Outlet } from "react-router-dom";

export function PublicLayout() {
  return (
    <div className="min-h-full flex items-center justify-center px-4 bg-bg">
      <div className="w-full max-w-md">
        <Outlet />
      </div>
    </div>
  );
}
