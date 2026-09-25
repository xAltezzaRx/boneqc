import { redirect } from "next/navigation";

import { DatasetDashboard } from "@/components/dataset-dashboard";
import { getCurrentUser } from "@/lib/api";


export default async function DatasetPage() {
  const user =
    await getCurrentUser();

  if (!user) {
    redirect("/login");
  }

  if (user.role !== "ADMIN") {
    redirect("/studies");
  }

  return (
    <DatasetDashboard />
  );
}
