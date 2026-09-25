"use client";

import {
  useParams,
} from "next/navigation";

import {
  ExpertWorkspace,
} from "@/components/expert-workspace";


export default function ExpertPage() {
  const params =
    useParams<{
      id: string;
    }>();

  return (
    <ExpertWorkspace
      studyId={
        params.id
      }
    />
  );
}
