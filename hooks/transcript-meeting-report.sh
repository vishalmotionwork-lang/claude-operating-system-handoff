#!/usr/bin/env bash
# PostToolUse(Bash) — fires when chatgpt_transcribe.sh is invoked.
# Reminds Claude to offer filing the transcript as a meeting report
# under ~/Workspace/meetings/YYYY-MM/<department>/
#
# Silent (exit 0, no output) for every other Bash command.

input=$(cat 2>/dev/null)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null)

case "$cmd" in
  *chatgpt_transcribe*)
    jq -n '{
      hookSpecificOutput: {
        hookEventName: "PostToolUse",
        additionalContext: (
          "A ChatGPT transcription was just invoked (chatgpt_transcribe.sh). "
          + "Once the transcript is complete, you MUST use AskUserQuestion to ask the user "
          + "whether to turn it into a meeting report — do not decide this yourself and do not skip it. "
          + "Offer: (a) yes, build the report, (b) no, transcript only. "
          + "If yes and the department is not obvious from the content, ask which one: "
          + "scripting / editing / designing / founders. "
          + "Then build it in the team meeting-notes HTML format and save to "
          + "~/Workspace/meetings/YYYY-MM/<department>/YYYY-MM-DD-<topic-slug>--<people>.html "
          + "following ~/Workspace/meetings/README.md (naming, asset depth, render check). "
          + "If the transcription was launched in the background, wait for it to finish before asking."
        )
      }
    }'
    ;;
esac

exit 0
