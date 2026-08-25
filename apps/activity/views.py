from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ActivityGateCheck, ActivitySession, ActivityStatusChange
from .serializers import ActivitySessionSummarySerializer, ActivitySyncRequestSerializer


class ActivitySyncView(APIView):
    """
    POST /api/activity/sync/

    Body: { "sessions": [ { clientSessionId, username, startTime, endTime,
                             totalActiveSeconds, totalAfkSeconds, totalBlockedSeconds,
                             gateChecks: [...], statusChanges: [...] }, ... ] }

    Backs up finished GapsSight sessions (and their GateChecks/StatusChanges
    detail rows) from the desktop app's local SQLite database into this
    server's database, so the desktop app can safely prune its own old
    detail rows (see ActivitySyncService/PruneOldPerformanceData on the
    client -- it only keeps a rolling ~10 day window locally) without
    losing the history for good.

    Idempotent: a session already present for this user (matched by
    clientSessionId, which is only unique per-device) is left untouched and
    its id is just echoed back in "syncedSessionIds" -- so if a previous
    sync response never made it back to the client (dropped connection,
    etc.) and it retries the same batch, nothing gets duplicated.

    Each authenticated user can only sync/see their own sessions -- there's
    no "sync as someone else" here, `owner` always comes from the request's
    JWT, never from the payload.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ActivitySyncRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        synced_ids = []
        skipped_ids = []

        with transaction.atomic():
            for session_data in serializer.validated_data["sessions"]:
                client_session_id = session_data["client_session_id"]
                gate_checks = session_data.pop("gate_checks", [])
                status_changes = session_data.pop("status_changes", [])

                existing = ActivitySession.objects.filter(
                    owner=request.user, client_session_id=client_session_id
                ).first()
                if existing is not None:
                    # Already backed up from an earlier sync -- report it as
                    # synced anyway so the client marks it done locally and
                    # stops retrying it, but don't touch the stored rows.
                    skipped_ids.append(client_session_id)
                    synced_ids.append(client_session_id)
                    continue

                session = ActivitySession.objects.create(owner=request.user, **session_data)

                if gate_checks:
                    ActivityGateCheck.objects.bulk_create(
                        [ActivityGateCheck(session=session, **row) for row in gate_checks]
                    )
                if status_changes:
                    ActivityStatusChange.objects.bulk_create(
                        [ActivityStatusChange(session=session, **row) for row in status_changes]
                    )

                synced_ids.append(client_session_id)

        return Response(
            {"syncedSessionIds": synced_ids, "alreadySynced": skipped_ids},
            status=status.HTTP_200_OK,
        )


class MyActivitySessionsView(generics.ListAPIView):
    """
    GET /api/activity/sessions/ -- read-only list of the current user's own
    synced sessions (most recent first), mainly to confirm a sync actually
    landed. Not used by the desktop app itself.
    """

    serializer_class = ActivitySessionSummarySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ActivitySession.objects.filter(owner=self.request.user)
