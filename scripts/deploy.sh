#!/bin/bash
# Package the ingest and synthesis Lambdas from src/ and deploy the stack. Run from the repository
# root after `source .byeori.env`. Both function packages go through the data bucket under cfn/.
#
# IngestReasoning moved from xhigh to high on 2026-09-22 by the user's decision. The effort tells
# the model how much to deliberate; it also sets the output allowance through
# ingest_lambda.THINKING_HEADROOM, but that ceiling has never bound (the largest output among the
# 441 notes that passed that day was 16,896 tokens against an allowance of 64,000). So the change
# makes the model think less, not get cut off. Thinking is billed as output, which was 54% of an
# evidence note's cost that day, and that is where the saving comes from. Synthesis keeps xhigh
# through the lab stack's ResearchReasoning; the answer worker records high but sends no thinking
# at all, because forced tool choice excludes it.
#
# Evidence notes moved to Opus 5.5 on 2026-09-23 by the user's decision; answers and synthesis stay
# on DraftModelId. On that day's measurement Opus 5.5 wrote a note for 22% less than Opus 5 at the
# same effort and two blind reviewers preferred it on 4 of 6 papers, but its biology classifier
# declined 9 of 40 noted papers (17% weighted by category), so NoteFallbackModelId writes those.
#
# Synthesis got its own SynthesisModelId and SynthesisReasoning the same day; until then it shared
# DraftModelId and IngestReasoning, which had taken it to high with the notes on 2026-09-22. Opus 5.5
# declined all four trial synthesis calls at xhigh (content_filtered), and the user still chose it,
# at high, with SynthesisFallbackModelId (Opus 5, same effort) writing whatever it declines.
#
# Later that day the user put every model back on Opus 5 for the time being, because of Opus 5.5's
# safety filtering ("우리 사용을 당분간 모두 5로 합시다").
#
# Notes went back to Opus 5.5 at high on 2026-09-25, after synthesis did. What decided it: Opus 5
# had declined klein-2023-genot three times with content_filtered and Opus 5.5 wrote it in one call,
# 88 seconds, seven sections, $0.38. Refusal is not a property of the model but of the pairing, so
# NoteFallbackModelId stays Opus 5 and writes whatever 5.5 declines - the 2026-09-23 measurement of
# 9 declines in 40 notes is the rate that fallback now absorbs, and source_note_written_by records
# which model wrote each one.
#
# Synthesis went back to Opus 5.5 at high on 2026-09-24. The 2026-09-23 refusals were at xhigh; a
# trial page at high (spatial-seq/pretrained-foundation-models, the same page Opus 5 had written)
# came back ready in one call, 20% cheaper, and found what Opus 5 had missed - that HEIST attributes
# scGPT-spatial's advantage to pretraining on the evaluation dataset and admits overlap with its own
# baselines. SynthesisFallbackModelId stays Opus 5, so a page 5.5 declines is written by 5 in the
# same call and the run's fallback_calls counts how often that happens.
set -euo pipefail
: "${AWS_KIRO_WIKI_BUCKET:?source .byeori.env first}"
: "${KIRO_WIKI_STACK:?source .byeori.env first}"
: "${KIRO_WIKI_OPENALEX_PARAMETER:?source .byeori.env first}"
if [ "${KIRO_WIKI_CREATE_VPC:-false}" != "true" ]; then
  : "${KIRO_WIKI_VPC_ID:?set KIRO_WIKI_VPC_ID and KIRO_WIKI_SUBNET_IDS, or KIRO_WIKI_CREATE_VPC=true}"
  : "${KIRO_WIKI_SUBNET_IDS:?set KIRO_WIKI_SUBNET_IDS (comma-separated public subnet ids)}"
fi
# Lab mode (KIRO_WIKI_REQUIRE_ORIGIN_MAIN=1, set in the lab's env file): the stack packages this
# working tree, so a tree missing another machine's pushed commits removes their code from the
# Lambdas. On 2026-09-23 two Macs did this to each other within an hour. The same mode refuses an
# empty contact address, so a deploy from a stale env file cannot drop the lab's polite-pool e-mail.
# A standalone install has no origin/main to compare with and skips both checks.
if [ "${KIRO_WIKI_REQUIRE_ORIGIN_MAIN:-}" = "1" ]; then
  : "${KIRO_WIKI_CONTACT_EMAIL:?lab mode needs KIRO_WIKI_CONTACT_EMAIL; source .byeori.env first}"
  git fetch --quiet origin
  if ! git merge-base --is-ancestor origin/main HEAD; then
    echo "deploy.sh: this tree lacks commits already on origin/main; merge them before deploying" >&2
    exit 1
  fi
fi
packaged="state/packaged-template.yaml"
aws cloudformation package \
  --template-file infra/template.yaml \
  --s3-bucket "$AWS_KIRO_WIKI_BUCKET" --s3-prefix cfn \
  --output-template-file "$packaged"
python3 scripts/preserve_template_syntax.py infra/template.yaml "$packaged"
aws cloudformation deploy \
  --template-file "$packaged" \
  --s3-bucket "$AWS_KIRO_WIKI_BUCKET" --s3-prefix cfn \
  --stack-name "$KIRO_WIKI_STACK" \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    RetentionDays=0 \
    OpenAlexApiKeyParameterName="$KIRO_WIKI_OPENALEX_PARAMETER" \
    ContactEmail="${KIRO_WIKI_CONTACT_EMAIL:-}" \
    DraftModelId=global.anthropic.claude-opus-5 \
    NoteModelId=global.anthropic.claude-opus-5-5 \
    NoteFallbackModelId=global.anthropic.claude-opus-5 \
    SynthesisModelId=global.anthropic.claude-opus-5-5 \
    SynthesisFallbackModelId=global.anthropic.claude-opus-5 \
    SynthesisReasoning=high \
    IngestReasoning=high \
    QuestionBudgetUsd=12 \
    VpcId="${KIRO_WIKI_VPC_ID:-}" \
    ExtractionSubnets="${KIRO_WIKI_SUBNET_IDS:-}" \
    CreateVpc="${KIRO_WIKI_CREATE_VPC:-false}" \
    "$@"
aws cloudformation describe-stacks --stack-name "$KIRO_WIKI_STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='SynthesisFunctionName' || OutputKey=='SynthesisStateMachineArn'].[OutputKey,OutputValue]" \
  --output table
