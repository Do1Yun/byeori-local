# What Byeori costs

Three numbers matter: what one paper costs, what one question costs, and what the system costs
in a month when nobody uses it.

These are **one lab's numbers**, measured in that lab's account in September 2026 at Bedrock's
list prices in US dollars, before tax. Your papers, questions, region and model choice will give
different ones. To read your own, open **Billing → Cost Explorer** in the AWS console, set the
date range, and group or filter by "Service": Bedrock appears as "Amazon Bedrock" (or under the
Claude model's own name), next to "Amazon Simple Storage Service", "AWS Lambda" and the others.
Cost Explorer lags by about a day. The stack also records each note's token counts in the catalog
table, and `uv run byeori cost-ledger` summarises the time and estimated cost of the steps run
from your computer.

## Per paper

The evidence note is almost the whole cost of a paper. These are the lab's notes, priced from the
input and output tokens the catalog table records for each one, at Bedrock list prices with no
prompt caching:

| Model | Notes measured | One paper (median) | 1,000 papers |
|---|---:|---:|---:|
| Claude Opus 5.5 (what `byeori deploy` sets) | 52 | $0.244 | about $244 |
| Claude Opus 5 (the fallback, and the template default) | 12,807 | $0.375 | about $375 |

Add about $0.02 per paper for the rest: GROBID extraction and the figure worker on Fargate (about
a cent together) and the OpenAlex lookups.

Two things move the note's cost. A long paper reads more tokens: the median note read about 25,000
input tokens and wrote about 9,800, thinking included. And "thinking" (`IngestReasoning`, which
the installer deploys at `high`) is billed as output; set `IngestReasoning=default` in
`byeori deploy` for no thinking. When Opus 5.5 declines a paper, Opus 5 writes it in the same call,
so that paper costs both calls.

## Per question

- **A research question** (an administrator's question that may read originals and write
  synthesis pages): with a budget of $12 per question (`QuestionBudgetUsd`), six questions the lab
  ran on 2026-09-23 cost $13.25 together, a median of **$2.21** per question. The budget is a
  ceiling at which the question stops and writes its answer, not a typical cost.
- **A student answer** (the optional student service; answer-only, at most two model calls):
  about **$0.25**. Twenty answers asked at once cost $5.06.
- **Jev triage** (optional): a fraction of a cent per answer; see `docs/JEV.md`.

## Idle month

When nobody adds papers or asks questions:

- **S3**: billed by stored size, about $0.023 per GB-month in us-east-1. A PDF with its extraction
  and note takes a few megabytes, so a thousand papers is a few gigabytes: well under a dollar.
- **KMS**: $1 per key-month for the key the student service and Jev use (`docs/INSTALL.md` step 7);
  nothing if you did not create it.
- **Everything else** (Lambda, Fargate, Step Functions, DynamoDB, Bedrock, EventBridge,
  CloudFormation, IAM, Parameter Store): near zero. They bill only while they work, and the
  nightly index rebuild is one short function run. The student service's one-minute relay is a
  small Lambda that finds nothing to do.
