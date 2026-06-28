import time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from plant3d.models import ConversionJob
from plant3d.services import execute_conversion_job


class Command(BaseCommand):
    help = "Process a queued plant3d conversion job."

    def add_arguments(self, parser):
        parser.add_argument("job_id", nargs="?", type=int)
        parser.add_argument("--next", action="store_true", help="Process the oldest queued job.")
        parser.add_argument("--all", action="store_true", help="Process every queued job in FIFO order.")
        parser.add_argument("--watch", action="store_true", help="Keep polling for queued jobs until stopped.")
        parser.add_argument("--poll-interval", type=float, default=2.0, help="Seconds to wait between watch polls.")
        parser.add_argument("--idle-exit-seconds", type=float, default=None, help="Exit watch mode after this many idle seconds.")
        parser.add_argument("--max-jobs", type=int, default=None, help="Stop after processing this many jobs in watch mode.")

    def handle(self, *args, **options):
        job_id = options.get("job_id")
        use_next = options.get("next")
        use_all = options.get("all")
        use_watch = options.get("watch")
        selected_modes = sum(1 for value in (bool(job_id), use_next, use_all, use_watch) if value)
        if selected_modes != 1:
            raise CommandError("Provide exactly one of job_id, --next, --all, or --watch.")

        if use_watch:
            self._watch(
                poll_interval=max(float(options.get("poll_interval") or 0), 0.0),
                idle_exit_seconds=options.get("idle_exit_seconds"),
                max_jobs=options.get("max_jobs"),
            )
            return

        if use_all:
            processed_count = 0
            while True:
                job = self._next_queued_job()
                if job is None:
                    break
                self._process_job(job, accept_claimed=True)
                processed_count += 1
            if processed_count:
                self.stdout.write(self.style.SUCCESS(f"Processed {processed_count} plant3d queued job(s)."))
            else:
                self.stdout.write(self.style.WARNING("No queued plant3d conversion jobs."))
            return

        if use_next:
            job = self._next_queued_job()
            if job is None:
                self.stdout.write(self.style.WARNING("No queued plant3d conversion jobs."))
                return
        else:
            try:
                job = ConversionJob.objects.get(pk=job_id)
            except ConversionJob.DoesNotExist as exc:
                raise CommandError(f"Conversion job {job_id} does not exist.") from exc

        self._process_job(job, accept_claimed=use_next)

    def _next_queued_job(self):
        with transaction.atomic():
            job = (
                ConversionJob.objects.select_for_update(skip_locked=True)
                .filter(status="queued")
                .order_by("created_at", "pk")
                .first()
            )
            if job is None:
                return None
            job.status = "running"
            job.progress_percent = max(job.progress_percent, 1)
            job.started_at = job.started_at or timezone.now()
            job.error_message = ""
            job.save(update_fields=["status", "progress_percent", "started_at", "error_message", "updated_at"])
            return job

    def _watch(self, poll_interval, idle_exit_seconds=None, max_jobs=None):
        processed_count = 0
        idle_started = time.monotonic()
        self.stdout.write(self.style.SUCCESS("Watching for queued plant3d conversion jobs. Press Ctrl+C to stop."))
        while True:
            job = self._next_queued_job()
            if job is None:
                if idle_exit_seconds is not None and time.monotonic() - idle_started >= float(idle_exit_seconds):
                    self.stdout.write(self.style.WARNING("No queued plant3d conversion jobs; watch idle timeout reached."))
                    return
                time.sleep(poll_interval)
                continue

            idle_started = time.monotonic()
            self._process_job(job, accept_claimed=True)
            processed_count += 1
            if max_jobs is not None and processed_count >= int(max_jobs):
                self.stdout.write(self.style.SUCCESS(f"Processed {processed_count} plant3d queued job(s); max-jobs reached."))
                return

    def _process_job(self, job, accept_claimed=False):
        execute_conversion_job(job, accept_claimed=accept_claimed)
        job.refresh_from_db()
        if job.status == "completed":
            self.stdout.write(self.style.SUCCESS(f"Processed plant3d job {job.pk}: completed."))
            return
        raise CommandError(f"Processed plant3d job {job.pk}: {job.status} - {job.error_message}")
