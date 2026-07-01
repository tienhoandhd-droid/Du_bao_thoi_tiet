#!/usr/bin/env bash
set -euo pipefail

readonly expected_project="bdttccztjtrcaztjgkot"
readonly expected_repo="tienhoandhd-droid/Du_bao_thoi_tiet"

die() {
  printf 'CRAVE_START_ERROR: %s\n' "$1" >&2
  exit 2
}

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || die "Không ở trong Git repository."
progress_file="$repo_root/PROJECT_PROGRESS.md"
skill_file="$repo_root/.agents/skills/crave-system-orchestrator/SKILL.md"
closure_manifest="$repo_root/docs/checkpoints/search-upgrade/P0-closure-readiness-manifest.json"
closure_validator="$repo_root/scripts/validate_p0_closure_manifest.py"

[[ -f "$progress_file" ]] || die "Thiếu PROJECT_PROGRESS.md."
[[ -f "$skill_file" ]] || die "Thiếu skill canonical."

metadata_value() {
  local key="$1"
  awk -v key="$key" '
    /^CRAVE_PROGRESS$/ { in_meta=1; next }
    /^END_CRAVE_PROGRESS$/ { in_meta=0 }
    in_meta && index($0, key ":") == 1 {
      sub("^[^:]+:[[:space:]]*", "")
      print
      exit
    }
  ' "$progress_file"
}

schema_version="$(metadata_value schema_version)"
project_id="$(metadata_value project_id)"
repository="$(metadata_value repository)"
branch="$(metadata_value branch)"
overall="$(metadata_value overall_decision)"
active_run="$(metadata_value active_run)"
active_action="$(metadata_value active_action)"
updated_at="$(metadata_value updated_at)"
updated_by="$(metadata_value updated_by)"
p0_review_policy="$(metadata_value p0_review_policy)"
review_gate="$(metadata_value review_gate)"
review_scope="$(metadata_value review_scope)"

[[ "$schema_version" == "1" ]] || die "schema_version phải là 1."
[[ "$project_id" == "$expected_project" ]] || die "Sai Supabase project ID."
[[ "$repository" == "$expected_repo" ]] || die "Sai repository identity."
[[ "$branch" == "main" ]] || die "Long-lived branch phải là main."
[[ -n "$active_run" && -n "$active_action" ]] || die "Thiếu active run/action."
[[ "$p0_review_policy" == "codex_final_check" ]] || die "p0_review_policy phải là codex_final_check."

active_rows="$(awk -F'|' '
  /^\| [A-Z0-9-]+ / {
    status=$4
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", status)
    gsub(/`/, "", status)
    if (status ~ /^(READY|IN_PROGRESS|LOCAL_TESTED|FINAL_CHECK|FINAL_CHECK_FAILED|FINAL_CHECK_PASS|READY_FOR_APPROVAL|USER_APPROVED|APPLIED|LIVE_VERIFIED)$/) {
      id=$2
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", id)
      print id ":" status
    }
  }
' "$progress_file")"

active_count="$(printf '%s\n' "$active_rows" | awk 'NF {count++} END {print count+0}')"
[[ "$active_count" == "1" ]] || die "Phải có đúng một action hoạt động; hiện có $active_count."

active_row_id="${active_rows%%:*}"
active_status="${active_rows#*:}"
[[ "$active_row_id" == "$active_action" ]] || die "Metadata active_action không khớp action table."

open_p0_blockers="$(awk -F'|' '
  /^\| BLK-[0-9]+ / {
    severity=$3
    status=$7
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", severity)
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", status)
    gsub(/`/, "", severity)
    gsub(/`/, "", status)
    if (severity == "P0" && status != "CLOSED" && status != "DONE") count++
  }
  END { print count+0 }
' "$progress_file")"

if [[ "$active_status" == "FINAL_CHECK" || "$active_status" == "FINAL_CHECK_PASS" ]]; then
  [[ "$review_gate" =~ ^(P0|P1|FULL)$ ]] || die "FINAL_CHECK thiếu review_gate hợp lệ."
  if [[ "$review_gate" == "P0" ]]; then
    [[ "$active_action" == "P0-FINAL-CHECK" ]] || die "P0 final check chỉ hợp lệ cho action P0-FINAL-CHECK."
    [[ "$review_scope" == "CONSOLIDATED_P0" ]] || die "P0 final check chỉ hợp lệ với review_scope CONSOLIDATED_P0."
    [[ "$open_p0_blockers" == "0" ]] || die "Không được mở Codex P0 final check khi còn $open_p0_blockers blocker P0."
    [[ -f "$closure_validator" ]] || die "Thiếu P0 closure manifest validator."
    python3 "$closure_validator" "$closure_manifest" \
      --progress-updated-at "$updated_at" \
      || die "P0 closure manifest thiếu, stale hoặc chưa PASS đủ dependency/evidence."
  fi
else
  [[ "$review_gate" == "NONE" && "$review_scope" == "NONE" ]] || die "Action chưa final check phải có review_gate/review_scope NONE."
fi

current_branch="$(git -C "$repo_root" branch --show-current)"
[[ "$current_branch" == "main" ]] || die "Worktree hiện tại không ở nhánh main."

printf '%s\n' '══════════════════════════════════════════════════════'
printf '%s\n' ' CRAVE — SESSION START'
printf '%s\n' '══════════════════════════════════════════════════════'
printf 'Repo root: %s\n' "$repo_root"
printf 'Canonical skill: %s\n' "$skill_file"
printf 'Overall: %s\n' "$overall"
printf 'Active run: %s\n' "$active_run"
printf 'Active action: %s\n' "$active_action"
printf 'Action status: %s\n' "$active_status"
printf 'Progress updated: %s by %s\n' "$updated_at" "$updated_by"
printf 'P0 review policy: %s (open blockers: %s)\n' "$p0_review_policy" "$open_p0_blockers"

printf '\n%s\n' '--- Git status (read-only) ---'
git -C "$repo_root" status --short --branch

printf '\n%s\n' '--- PROJECT_PROGRESS.md ---'
sed -n '1,260p' "$progress_file"

printf '\n%s\n' '--- Agent instruction ---'
if [[ "$active_status" == "FINAL_CHECK" ]]; then
  printf 'Codex GPT: chạy consolidated %s final check (%s), tự remediation nếu FAIL.\n' "$review_gate" "$review_scope"
  printf '%s\n' 'Claude Code: CLAUDE_NOT_PARTICIPATING; không review/verify hoạt động này.'
elif [[ "$active_status" == "FINAL_CHECK_PASS" ]]; then
  printf 'Codex GPT: consolidated %s final check (%s) đã PASS; chỉ mở action tiếp theo khi progress được cập nhật có chủ đích.\n' "$review_gate" "$review_scope"
  printf '%s\n' 'Claude Code: CLAUDE_NOT_PARTICIPATING; không review/verify hoạt động này.'
else
  printf '%s\n' 'Codex GPT: lập plan ngắn và thực hiện đúng active action trong scope.'
  printf '%s\n' 'Claude Code: CLAUDE_NOT_PARTICIPATING; không review/verify hoạt động này.'
fi
printf '%s\n' 'Live/remote mutation vẫn phải qua approval ledger và xác nhận riêng.'
