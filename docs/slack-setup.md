# Slack setup: workspace, #oncall channel and app

Lab 3 posts the agent's analysis to Slack with **Approve / Reject** buttons. You need a workspace,
a channel, and a small Slack app with an incoming webhook and interactivity. No bot token or
OAuth scopes beyond the webhook are needed. About 10 minutes, best done before the workshop.

## 1. Workspace, channel and approvers

1. **Workspace** — go to slack.com/get-started → **Create a new workspace** and sign in with your email.
   The free plan is enough. Name it, for example `devfest-sre-lab`. As its owner you can install apps
   without an admin. (Company workspace: an admin may have to approve the app.)
2. **Channel** — in the sidebar, **Channels → + → Create a channel**, name it `oncall`.
   Public or private both work; for a private channel, be a member before adding the webhook.
3. **Approvers** — **Invite people** with the teammates who may press Approve. They must be members
   of the workspace.
4. **Member IDs** — for each approver: open their profile → **⋮ More → Copy member ID** (starts with `U`).

   ```bash
   export SLACK_APPROVERS=U0123ABCD,U0456EFGH   # only these IDs can approve or reject
   ```

## 2. The Slack app

1. **Create** — api.slack.com/apps → **Create New App → From scratch**. Name: `SRE Agent`;
   workspace: the one from step 1.
2. **Incoming webhook** — **Features → Incoming Webhooks → Activate: On**, then **Add New Webhook**,
   pick `#oncall` and **Allow**. Copy the URL (`https://hooks.slack.com/services/…`).
3. **Signing secret** — **Settings → Basic Information → App Credentials → Signing Secret → Show**, copy it.
4. **Store both** in Secret Manager (input is hidden; press Enter to skip SMTP):

   ```bash
   ./scripts/06-notify-secrets.sh
   ```

5. **Deploy the agent** — it prints the URL Slack must call:

   ```bash
   AUTONOMY=approve ./scripts/04-deploy-agent.sh
   # Slack app → Interactivity → Request URL: https://sre-agent-….run.app/slack/actions
   ```

6. **Buttons** — **Features → Interactivity & Shortcuts → On**, paste that Request URL, **Save Changes**.
7. **Test** — `./scripts/05-simulate-alert.sh`; within a minute `#oncall` shows the analysis with
   Approve / Reject.

Treat the webhook URL and signing secret like passwords: paste them only into `06-notify-secrets.sh`,
never into chat, code or a commit. Anyone with the webhook URL can post into `#oncall`.

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| No message in Slack | Webhook secret not stored or agent not redeployed: run `06-notify-secrets.sh`, then `04-deploy-agent.sh` |
| Buttons do nothing / Slack shows an error | Interactivity off or wrong Request URL (must end in `/slack/actions`) |
| "You are not on the approver list" | Your member ID is missing from `SLACK_APPROVERS`; export it and redeploy |
| Click rejected with 401 in the agent logs | Wrong signing secret: re-run `06-notify-secrets.sh`, then redeploy |
| Org blocks public Cloud Run services | Slack can't reach the agent; approve with `./scripts/incidents.sh approve <id>` |
