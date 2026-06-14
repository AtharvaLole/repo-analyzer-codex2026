import { RepoWorkspace } from "@/components/RepoWorkspace";

type RepoPageProps = {
  params: {
    repoId: string;
  };
};

export default function RepoPage({ params }: RepoPageProps) {
  const repoId = decodeURIComponent(params.repoId);

  return <RepoWorkspace repoId={repoId} />;
}
