import type { StoryState } from "../../api/types";
import { Paragraphs } from "../../components/Paragraphs";
import { SceneImageView } from "./SceneImageView";
import { useSceneImages, versionsForTurn } from "./sceneImages";
import "./ChatFeed.css";

/** The story as a chat: the narrator's text as bubbles on the left, the
 *  player's inputs on the right. A turn's scene pictures hang on the
 *  narrator's bubble they were generated for. */
export function ChatFeed({ runId, story, name }: { runId: string; story: StoryState; name: string }) {
  const { images } = useSceneImages(runId);
  return (
    <>
      {story.initialization && (
        <NarratorBubble
          runId={runId}
          name={name}
          text={story.initialization.narration}
          versions={versionsForTurn(images, 0)}
        />
      )}
      {story.turns.map((turn) => (
        <div className="chat-exchange" key={turn.id}>
          <div className="chat-row chat-row--player">
            <div className="chat-bubble chat-bubble--player">
              <Paragraphs text={turn.player_input} />
            </div>
          </div>
          <NarratorBubble
            runId={runId}
            name={name}
            text={turn.narration}
            versions={versionsForTurn(images, turn.sequence)}
          />
        </div>
      ))}
    </>
  );
}

function NarratorBubble({
  runId,
  name,
  text,
  versions,
}: {
  runId: string;
  name: string;
  text: string;
  versions: ReturnType<typeof versionsForTurn>;
}) {
  return (
    <div className="chat-row chat-row--narrator">
      <div className="chat-bubble chat-bubble--narrator">
        <SceneImageView
          runId={runId}
          versions={versions}
          fallbackAlt={name}
          className="chat-scene-art"
          hideWhenEmpty
        />
        <Paragraphs text={text} />
      </div>
    </div>
  );
}
