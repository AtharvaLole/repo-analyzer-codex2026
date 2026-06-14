import { RepoChatRoute } from "@/components/RepoChatRoute";

type ChatPageProps = {
  params: {
    repoId: string;
  };
};

export default function ChatPage({ params }: ChatPageProps) {
  const repoId = decodeURIComponent(params.repoId);

  return <RepoChatRoute repoId={repoId} />;
}
