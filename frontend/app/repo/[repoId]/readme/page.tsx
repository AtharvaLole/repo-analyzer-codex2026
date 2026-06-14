import { ReadmePreview } from "@/components/ReadmePreview";

type ReadmePageProps = {
  params: {
    repoId: string;
  };
};

export default function ReadmePage({ params }: ReadmePageProps) {
  const repoId = decodeURIComponent(params.repoId);

  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs font-semibold uppercase text-amber-700">README generator</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-normal">{repoId}</h1>
      </div>
      <ReadmePreview repoId={repoId} />
    </div>
  );
}
