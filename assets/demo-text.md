The notification never arrived because the workflow skipped the email step. The subscriber has `email: false` in their channel preferences, so the preference check ran before rendering and marked the step as skipped.

Three things line up in the execution log:

1. **Trigger accepted.** The API returned `201` and queued job `job_8f2c`.
2. **Preference check.** The worker loaded the subscriber and found email disabled at the workflow level, not the global level.
3. **Step skipped.** No template was rendered and no provider was called, so SendGrid has no record of it.

To confirm, open the activity feed for this subscriber and expand the workflow run. The email step shows `skipped: preference`. If the subscriber should receive this email, either turn the channel back on for them or mark the workflow as critical so it ignores preferences.
