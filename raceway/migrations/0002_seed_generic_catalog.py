from django.db import migrations


GENERIC_CATALOG = [
    {
        "code": "LADDER-HDG",
        "name": "Ladder HDG",
        "kind": "ladder",
        "material": "HDG steel",
        "standard_length_mm": 3000,
        "standard_basis": "IEC 61537",
        "profile": {"proxy_kind": "ladder", "catalogue_basis": "generic"},
        "metadata": {"seed": "generic_vendor_free", "stage": "raceway_mvp"},
        "sizes": [
            {"width_mm": 300, "depth_mm": 100},
            {"width_mm": 450, "depth_mm": 100},
            {"width_mm": 600, "depth_mm": 150},
        ],
    },
    {
        "code": "PERF-HDG",
        "name": "Perforated HDG",
        "kind": "perforated_tray",
        "material": "HDG steel",
        "standard_length_mm": 3000,
        "standard_basis": "IEC 61537",
        "profile": {"proxy_kind": "perforated_tray", "catalogue_basis": "generic"},
        "metadata": {"seed": "generic_vendor_free", "stage": "raceway_mvp"},
        "sizes": [
            {"width_mm": 150, "depth_mm": 50},
            {"width_mm": 300, "depth_mm": 75},
            {"width_mm": 450, "depth_mm": 100},
        ],
    },
]


def seed_generic_catalog(apps, schema_editor):
    RacewayFamily = apps.get_model("raceway", "RacewayFamily")
    RacewaySize = apps.get_model("raceway", "RacewaySize")

    for family_data in GENERIC_CATALOG:
        sizes = family_data["sizes"]
        family_defaults = {
            key: value
            for key, value in family_data.items()
            if key != "sizes"
        }
        family, created = RacewayFamily.objects.get_or_create(
            code=family_data["code"],
            defaults={**family_defaults, "is_active": True, "is_validated": False},
        )
        if created:
            family.is_validated = False
            family.save(update_fields=["is_validated"])
        for size_data in sizes:
            RacewaySize.objects.get_or_create(
                family=family,
                width_mm=size_data["width_mm"],
                depth_mm=size_data["depth_mm"],
                defaults={"is_active": True},
            )


class Migration(migrations.Migration):

    dependencies = [
        ("raceway", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_generic_catalog, reverse_code=migrations.RunPython.noop),
    ]
