import { Outlet } from "react-router-dom";

export function PublicLayout() {
  return (
    <div className="h-full flex items-center justify-center px-4 bg-bg overflow-y-auto">
      <div className="w-full max-w-md py-6">
        <Outlet />
      </div>
    </div>
  );
}
