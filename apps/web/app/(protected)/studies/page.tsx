import { redirect } from "next/navigation";

import { StudyWorklist } from "@/components/study-worklist";
import { getCurrentUser } from "@/lib/api";


export default async function StudiesPage() {
  const user =
    await getCurrentUser();

  if (!user) {
    redirect("/login");
  }

  return (
    <StudyWorklist
      currentRole={user.role}
    />
  );
}
