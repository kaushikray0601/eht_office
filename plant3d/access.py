from .models import ConversionJob, ModelObject, RenderPackage, RenderTile, SourceModel
from .project_gateway import accessible_project_ids


def source_models_for_user(user):
    return SourceModel.objects.filter(project_id__in=accessible_project_ids(user))


def render_packages_for_user(user):
    return RenderPackage.objects.filter(source_model__project_id__in=accessible_project_ids(user))


def render_tiles_for_user(user):
    return RenderTile.objects.filter(render_package__source_model__project_id__in=accessible_project_ids(user))


def conversion_jobs_for_user(user):
    return ConversionJob.objects.filter(source_model__project_id__in=accessible_project_ids(user))


def model_objects_for_user(user):
    return ModelObject.objects.filter(source_model__project_id__in=accessible_project_ids(user))
