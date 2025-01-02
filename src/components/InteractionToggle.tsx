import { Button } from "@/components/ui/button";
import { MessageSquare, BookOpen } from "lucide-react";

interface InteractionToggleProps {
  mode: "chat" | "quiz";
  onModeChange: (mode: "chat" | "quiz") => void;
}

export function InteractionToggle({ mode, onModeChange }: InteractionToggleProps) {
  return (
    <div className="flex gap-2">
      <Button
        variant={mode === "chat" ? "default" : "outline"}
        onClick={() => onModeChange("chat")}
      >
        <MessageSquare className="mr-2 h-4 w-4" />
        Chat
      </Button>
      <Button
        variant={mode === "quiz" ? "default" : "outline"}
        onClick={() => onModeChange("quiz")}
      >
        <BookOpen className="mr-2 h-4 w-4" />
        Quiz
      </Button>
    </div>
  );
}