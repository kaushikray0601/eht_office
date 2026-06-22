from django.core.management.base import BaseCommand, CommandError

from plant3d.models import ConversionJob
from plant3d.services import execute_conversion_job


class Command(BaseCommand):
    help = "Process a queued plant3d conversion job."

    def add_arguments(self, parser):
        parser.add_argument("job_id", nargs="?", type=int)
        parser.add_argument("--next", action="store_true", help="Process the oldest queued job.")
        parser.add_argument("--all", action="store_true", help="Process every queued job in FIFO order.")

    def handle(self, *args, **options):
        job_id = options.get("job_id")
        use_next = options.get("next")
        use_all = options.get("all")
        selected_modes = sum(1 for value in (bool(job_id), use_next, use_all) if value)
        if selected_modes != 1:
            raise CommandError("Provide exactly one of job_id, --next, or --all.")

        if use_all:
            processed_count = 0
            while True:
                job = ConversionJob.objects.filter(status="queued").order_by("created_at", "pk").first()
                if job is None:
                    break
                self._process_job(job)
                processed_count += 1
            if processed_count:
                self.stdout.write(self.style.SUCCESS(f"Processed {processed_count} plant3d queued job(s)."))
            else:
                self.stdout.write(self.style.WARNING("No queued plant3d conversion jobs."))
            return

        if use_next:
            job = ConversionJob.objects.filter(status="queued").order_by("created_at", "pk").first()
            if job is None:
                self.stdout.write(self.style.WARNING("No queued plant3d conversion jobs."))
                return
        else:
            try:
                job = ConversionJob.objects.get(pk=job_id)
            except ConversionJob.DoesNotExist as exc:
                raise CommandError(f"Conversion job {job_id} does not exist.") from exc

        self._process_job(job)

    def _process_job(self, job):
        execute_conversion_job(job)
        job.refresh_from_db()
        if job.status == "completed":
            self.stdout.write(self.style.SUCCESS(f"Processed plant3d job {job.pk}: completed."))
            return
        raise CommandError(f"Processed plant3d job {job.pk}: {job.status} - {job.error_message}")
