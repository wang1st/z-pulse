I will perform the following actions to address your requests:

1.  **Frontend: Unify Article Management UI**
    *   Update `frontend/app/admin/articles/page.tsx` to match the **Indigo/Purple** theme used in the Accounts page (replacing the Green theme).
    *   Ensure all "Collection" related buttons and logic are completely removed, leaving only the article list and search/filter functions.
    *   This ensures consistent visual style (gradients, icons, colors) across the admin panel.

2.  **Backend: Operations & Troubleshooting**
    *   **Clear Tasks & Fix "Jan 5th" Issue**: The issue of not fetching articles after Jan 5th is likely due to a stuck `rss-bridge` process or an expired WeChat session (common with we-mp-rss). I will restart the `rss-bridge` and `ingestion-worker` containers. This effectively "clears" any stuck tasks and forces a fresh session/state.
    *   **Scheduled Tasks**: I will verify that the `ingestion-worker` is configured to run automatically (preset to run every 30 minutes). I will explain how this works so you can rely on it instead of manual collection.

3.  **Deployment**
    *   Rebuild and deploy the frontend to apply the UI changes.
    *   Restart backend services to apply the operational fixes.

**Wait for your confirmation to proceed.**