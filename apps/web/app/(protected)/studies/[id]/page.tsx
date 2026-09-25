"use client";

import {
  useParams,
} from "next/navigation";

import {
  StudyViewer,
} from "@/components/study-viewer";


export default function StudyPage() {
  const params =
    useParams<{
      id: string;
    }>();

  return (
    <StudyViewer
      studyId={params.id}
    />
  );
}
